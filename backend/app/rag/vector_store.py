"""
Vector Store Abstraction (Qdrant)

Wraps the Qdrant client for storing and searching document chunk embeddings.

Operations:
- ensure_collection(): Create the collection if it doesn't exist
- upsert_chunks(): Store chunk vectors with metadata (document_id, text, page, etc.)
- search(): Find the top-K most similar chunks to a query vector
- delete_by_document(): Remove all chunks for a specific document (on document deletion)

Why Qdrant?
- Already in docker-compose, purpose-built for vector similarity search
- Supports filtering (e.g. search only within a user's documents)
- Persistent storage across restarts (vs. FAISS in-memory which loses data)
- gRPC support for high-throughput production use

The in-memory mode (QdrantClient(":memory:")) is used for testing — same API,
no server dependency. This is the "thin fallback" mentioned in the design.
"""

import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.rag.chunker import DocumentChunk
from app.rag.embeddings import EMBEDDING_DIMENSION

# Default collection name (configurable via settings.QDRANT_COLLECTION)
DEFAULT_COLLECTION = "documents"


class VectorStoreError(Exception):
    """Raised when vector store operations fail."""
    pass


class VectorStore:
    """
    Qdrant-backed vector store for RAG chunk storage and retrieval.

    Thread-safety: QdrantClient is thread-safe for reads. Writes are
    serialized by Qdrant server anyway. Safe to use as a singleton.
    """

    def __init__(self, client: Optional[QdrantClient] = None, collection_name: Optional[str] = None):
        """
        Args:
            client: Optional pre-configured Qdrant client (for testing with :memory:).
                    If None, connects to the configured Qdrant server.
            collection_name: Override the collection name (defaults to settings).
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self._client = client

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )
        return self._client

    def ensure_collection(self) -> None:
        """Create the vector collection if it doesn't already exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        user_id: int,
    ) -> int:
        """
        Store chunk embeddings with metadata in Qdrant.

        Args:
            chunks: The document chunks (text + metadata)
            embeddings: Corresponding embedding vectors (same length as chunks)
            user_id: Owner's ID (used for filtering searches to user's docs)

        Returns:
            Number of points upserted

        Raises:
            VectorStoreError: If lengths don't match or Qdrant call fails
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length"
            )

        if not chunks:
            return 0

        self.ensure_collection()

        points = []
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk.text,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "user_id": user_id,
            }
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            ))

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            return len(points)
        except Exception as e:
            raise VectorStoreError(f"Failed to upsert chunks to Qdrant: {str(e)}") from e

    def search(
        self,
        query_vector: list[float],
        user_id: int,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Search for the most relevant chunks by cosine similarity.

        Filters results to only the requesting user's documents (multi-tenant
        isolation — users can't see each other's document content).

        Args:
            query_vector: The embedded question vector
            user_id: Only return chunks belonging to this user
            top_k: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1 for cosine)

        Returns:
            List of dicts: [{text, document_id, document_name, page_number,
                            chunk_index, score}], sorted by relevance desc.
        """
        self.ensure_collection()

        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
                limit=top_k,
                score_threshold=score_threshold,
            )

            return [
                {
                    "text": point.payload["text"],
                    "document_id": point.payload["document_id"],
                    "document_name": point.payload["document_name"],
                    "page_number": point.payload.get("page_number"),
                    "chunk_index": point.payload.get("chunk_index"),
                    "score": round(point.score, 4),
                }
                for point in results.points
            ]
        except Exception as e:
            raise VectorStoreError(f"Vector search failed: {str(e)}") from e

    def delete_by_document(self, document_id: int, user_id: int) -> None:
        """
        Delete all chunks for a specific document.

        Called when a user deletes a document from RAG — removes its
        vectors from the search index so they stop appearing in results.
        """
        self.ensure_collection()

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to delete document chunks: {str(e)}") from e

    def count_chunks(self, document_id: int, user_id: int) -> int:
        """Count how many chunks are stored for a specific document."""
        self.ensure_collection()

        try:
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
            )
            return result.count
        except Exception:
            return 0
