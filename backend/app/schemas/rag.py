"""
RAG Schemas (Pydantic)

Request/response contracts for document ingestion and retrieval-augmented queries.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ─── Ingest ────────────────────────────────────────────────────

class RAGIngestRequest(BaseModel):
    """Request to ingest a previously-uploaded document for RAG."""
    dataset_id: int = Field(..., description="ID of an uploaded PDF, Word, or text file")


class RAGDocumentResponse(BaseModel):
    """A document's RAG status."""
    id: int
    name: str
    file_type: str
    chunk_count: int
    embedding_status: str  # pending, processing, completed, failed
    created_at: datetime

    model_config = {"from_attributes": True}


class RAGDocumentListResponse(BaseModel):
    """List of user's RAG documents."""
    documents: list[RAGDocumentResponse]
    total: int


# ─── Query ─────────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    """Ask a question about your ingested documents."""
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20, description="Number of source chunks to retrieve")


class RAGSourceItem(BaseModel):
    """A single cited source chunk."""
    source_number: int
    document_name: str
    page_number: Optional[int] = None
    text: str
    score: float


class RAGQueryResponse(BaseModel):
    """Answer with cited sources."""
    answer: str
    sources: list[RAGSourceItem]
