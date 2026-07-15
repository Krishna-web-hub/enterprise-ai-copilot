"""
RAG (Retrieval-Augmented Generation) Endpoints

Handles document ingestion into the vector store and question-answering
grounded in retrieved document context with citations.

Routes:
- POST /ingest       → Process a document for RAG (chunk, embed, store)
- POST /query        → Ask a question, get answer with cited sources
- GET  /documents    → List ingested documents with their embedding status
- DELETE /documents/{id} → Remove a document from the RAG system
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.rag import (
    RAGDocumentListResponse,
    RAGDocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.services.rag_service import RAGService, RAGServiceError

router = APIRouter()


@router.post("/ingest", response_model=RAGDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and ingest a document for RAG.

    Supported file types: PDF (.pdf), Word (.docx), plain text (.txt).

    The document is:
    1. Saved to disk
    2. Text is extracted and split into overlapping chunks
    3. Each chunk is embedded (OpenAI text-embedding-3-small)
    4. Embeddings are stored in the vector database (Qdrant)

    After ingestion completes, the document's content is searchable
    via the /rag/query endpoint.
    """
    from pathlib import Path

    # Validate file type
    filename = file.filename or "unnamed"
    ext = Path(filename).suffix.lower()
    ext_to_type = {".pdf": "pdf", ".docx": "word", ".doc": "word", ".txt": "text"}

    if ext not in ext_to_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}' for RAG. Supported: .pdf, .docx, .txt",
        )

    file_type = ext_to_type[ext]

    # Read and save file
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    upload_dir = settings.upload_path / str(current_user.id) / "rag"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    file_path.write_bytes(content)

    # Create Document record
    document = Document(
        user_id=current_user.id,
        name=filename,
        file_path=str(file_path),
        file_type=file_type,
        embedding_status="pending",
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    # Ingest (chunk + embed + store)
    rag_service = RAGService(db)
    try:
        document = await rag_service.ingest_document(document, current_user.id)
    except RAGServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return document


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question about your ingested documents.

    The system:
    1. Embeds your question
    2. Finds the most relevant document chunks via semantic search
    3. Generates an answer grounded in those chunks
    4. Returns the answer with source citations [1], [2], etc.

    Each citation maps to a specific document and page number.
    """
    rag_service = RAGService(db)

    try:
        result = await rag_service.query(
            question=request.question,
            user_id=current_user.id,
            top_k=request.top_k,
        )
    except RAGServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    return RAGQueryResponse(**result)


@router.get("/documents", response_model=RAGDocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents ingested for RAG, with their embedding status."""
    rag_service = RAGService(db)
    documents = await rag_service.list_documents(current_user.id)
    return RAGDocumentListResponse(documents=documents, total=len(documents))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document from the RAG system.

    Removes the document record, its file from disk, and all of its
    chunks/embeddings from the vector store.
    """
    rag_service = RAGService(db)
    deleted = await rag_service.delete_document(document_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
