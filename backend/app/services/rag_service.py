"""
RAG Service — Document Ingestion and Retrieval-Augmented Generation

Orchestrates the two halves of the RAG pipeline:

1. INGEST: Upload a document → extract text → chunk → embed → store in Qdrant
   → update Document.embedding_status

2. QUERY: User asks a question → embed the question → search Qdrant for
   relevant chunks → LLM generates an answer grounded in those chunks
   → return answer with source citations

Why separate ingest from query?
- Ingestion is a write-heavy, one-time-per-document operation that
  involves API calls (embeddings) and disk IO (text extraction).
- Querying is a latency-sensitive, read-heavy operation that should
  feel instant (embed query + vector search + LLM = 2-3 seconds total).
- Keeping them separate means a slow ingestion never blocks query paths.

Citation system:
- The LLM prompt instructs the model to cite sources by bracketed numbers [1], [2]
- We pass up to 5 retrieved chunks as numbered sources
- The response includes both the generated answer and the full source list
  so the frontend can display "Source: policy.pdf, page 3" next to each citation
"""

import asyncio
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.rag.chunker import extract_and_chunk
from app.rag.embeddings import EmbeddingService, EmbeddingServiceError
from app.rag.vector_store import VectorStore, VectorStoreError
from app.services.llm_service import LLMService, LLMServiceError

# File types that support RAG ingestion (must have extractable text)
RAG_SUPPORTED_TYPES = {"pdf", "word", "text"}

# RAG query prompt
RAG_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions based ONLY on the \
provided source documents. Follow these rules strictly:

1. Answer the question using ONLY information from the provided sources.
2. Cite your sources using bracketed numbers like [1], [2], etc. corresponding to the source list.
3. If the sources do not contain enough information to answer the question, say so explicitly. \
Do NOT make up information or use knowledge outside the provided sources.
4. Be concise and direct. Provide specific details, numbers, and quotes from the sources.
5. If multiple sources support a claim, cite all of them.

Sources are provided in the format:
[N] Document: <name>, Page: <page> — <text excerpt>
"""


class RAGServiceError(Exception):
    """Raised for user-facing RAG errors."""
    pass


class RAGService:
    """Orchestrates RAG document ingestion and retrieval-augmented queries."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.llm_service = llm_service or LLMService()

    # ─── Ingest ─────────────────────────────────────────────────────

    async def ingest_document(self, document: Document, user_id: int) -> Document:
        """
        Process a document for RAG: extract text, chunk, embed, store.

        Updates Document.embedding_status through the lifecycle:
        - "processing" while working
        - "completed" on success
        - "failed" on error

        Runs the CPU-bound text extraction/chunking in a thread, then
        calls the embedding API, then stores vectors in Qdrant.

        Args:
            document: The Document ORM record (must already exist in DB)
            user_id: Owner's user ID

        Returns:
            Updated Document record with new embedding_status and chunk_count
        """
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise RAGServiceError(f"Document file not found: {document.file_path}")

        if document.file_type not in RAG_SUPPORTED_TYPES:
            raise RAGServiceError(
                f"Cannot ingest '{document.file_type}' files for RAG. "
                f"Supported: {', '.join(sorted(RAG_SUPPORTED_TYPES))}"
            )

        # Mark as processing
        document.embedding_status = "processing"
        await self.db.flush()

        try:
            # Step 1: Extract text and chunk (CPU-bound, run in thread)
            chunks = await asyncio.to_thread(
                extract_and_chunk,
                file_path=file_path,
                file_type=document.file_type,
                document_id=document.id,
                document_name=document.name,
            )

            if not chunks:
                document.embedding_status = "completed"
                document.chunk_count = 0
                await self.db.flush()
                return document

            # Step 2: Generate embeddings for all chunks
            chunk_texts = [c.text for c in chunks]
            embeddings = await self.embedding_service.embed_texts(chunk_texts)

            # Step 3: Store in Qdrant
            self.vector_store.upsert_chunks(chunks, embeddings, user_id)

            # Step 4: Update document status
            document.embedding_status = "completed"
            document.chunk_count = len(chunks)
            await self.db.flush()

            return document

        except (EmbeddingServiceError, VectorStoreError) as e:
            document.embedding_status = "failed"
            await self.db.flush()
            raise RAGServiceError(f"Ingestion failed: {str(e)}") from e

    # ─── Query ──────────────────────────────────────────────────────

    async def query(self, question: str, user_id: int, top_k: int = 5) -> dict:
        """
        Answer a question using retrieved document context (RAG).

        Pipeline:
        1. Embed the question
        2. Search Qdrant for the top-K most relevant chunks (user-filtered)
        3. Format sources as a numbered list for the LLM prompt
        4. LLM generates an answer citing those sources
        5. Return answer + source metadata for the frontend

        Args:
            question: The user's natural-language question
            user_id: Only search within this user's documents
            top_k: Number of chunks to retrieve (default 5)

        Returns:
            {
                "answer": str,  # LLM-generated answer with [N] citations
                "sources": [
                    {"document_name", "page_number", "text", "score", "source_number"}
                ]
            }

        Raises:
            RAGServiceError: If no documents are ingested or retrieval fails
        """
        # Step 1: Embed the question
        try:
            query_vector = await self.embedding_service.embed_query(question)
        except EmbeddingServiceError as e:
            raise RAGServiceError(f"Failed to embed question: {str(e)}") from e

        # Step 2: Search for relevant chunks
        try:
            results = self.vector_store.search(
                query_vector=query_vector,
                user_id=user_id,
                top_k=top_k,
            )
        except VectorStoreError as e:
            raise RAGServiceError(f"Vector search failed: {str(e)}") from e

        if not results:
            return {
                "answer": "I couldn't find any relevant information in your documents to answer this question. "
                          "Make sure you've uploaded and ingested documents related to your question.",
                "sources": [],
            }

        # Step 3: Format sources for the LLM prompt
        sources_text = self._format_sources_for_prompt(results)
        user_prompt = f"Sources:\n{sources_text}\n\nQuestion: {question}"

        # Step 4: Generate answer with citations
        try:
            answer = await self.llm_service.complete(
                system_prompt=RAG_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=1000,
                temperature=0.2,  # Slightly higher than NL2SQL for natural prose
            )
        except LLMServiceError as e:
            raise RAGServiceError(f"Failed to generate answer: {str(e)}") from e

        # Step 5: Build source metadata for the response
        sources = [
            {
                "source_number": i + 1,
                "document_name": r["document_name"],
                "page_number": r["page_number"],
                "text": r["text"][:200],  # Truncate for response payload size
                "score": r["score"],
            }
            for i, r in enumerate(results)
        ]

        return {"answer": answer, "sources": sources}

    # ─── Document Management ────────────────────────────────────────

    async def list_documents(self, user_id: int) -> list[Document]:
        """List all documents for a user (with embedding status)."""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, document_id: int, user_id: int) -> bool:
        """
        Delete a document and its vectors from Qdrant.

        Returns True if found and deleted, False if not found.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        # Remove vectors from Qdrant
        try:
            self.vector_store.delete_by_document(document_id, user_id)
        except VectorStoreError:
            pass  # Best-effort cleanup — don't fail the delete if Qdrant is down

        # Remove file from disk
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.db.delete(document)
        return True

    # ─── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _format_sources_for_prompt(results: list[dict]) -> str:
        """Format retrieved chunks as a numbered source list for the LLM."""
        lines = []
        for i, r in enumerate(results, start=1):
            page_str = f"Page: {r['page_number']}" if r.get("page_number") else "Page: N/A"
            lines.append(f"[{i}] Document: {r['document_name']}, {page_str} — {r['text']}")
        return "\n\n".join(lines)
