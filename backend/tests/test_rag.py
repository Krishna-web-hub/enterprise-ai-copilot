"""
Phase 7 Tests - RAG Pipeline (Document Ingestion & Retrieval-Augmented Q&A)

Coverage:
1. Chunker unit tests: verify text splitting produces expected chunks with metadata
2. Vector store unit tests: upsert + search + delete using in-memory Qdrant
3. Full endpoint integration tests: upload, ingest (mocked embeddings), query
   (mocked embeddings + mocked LLM), list, delete
4. Error handling: unsupported file types, missing documents, auth

Embedding and LLM calls are mocked — tests don't need an OpenAI API key.
Vector store tests use Qdrant's in-memory mode (no server needed).
Database/client/auth fixtures come from conftest.py.
"""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from httpx import AsyncClient
from qdrant_client import QdrantClient

from app.rag.chunker import DocumentChunk, _chunk_plain_text, extract_and_chunk
from app.rag.vector_store import VectorStore

# ─── Chunker Unit Tests ─────────────────────────────────────────

class TestChunker:
    """Tests for the document text splitting logic."""

    def test_chunks_plain_text(self):
        text = "First paragraph with enough content to be a chunk. " * 5 + "\n\n" + \
               "Second paragraph also with substantial content here. " * 5
        chunks = _chunk_plain_text(text, document_id=1, document_name="test.txt",
                                   chunk_size=200, chunk_overlap=30)
        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.document_id == 1 for c in chunks)
        assert all(c.document_name == "test.txt" for c in chunks)
        # Chunk indices are sequential
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_empty_text_produces_no_chunks(self):
        chunks = _chunk_plain_text("", document_id=1, document_name="empty.txt",
                                   chunk_size=200, chunk_overlap=30)
        assert chunks == []

    def test_chunks_preserve_content(self):
        """All original text should appear in at least one chunk."""
        text = "The quick brown fox jumps over the lazy dog. " * 20
        chunks = _chunk_plain_text(text, document_id=1, document_name="fox.txt",
                                   chunk_size=100, chunk_overlap=20)
        combined = " ".join(c.text for c in chunks)
        # Key phrases from the text should survive chunking
        assert "quick brown fox" in combined
        assert "lazy dog" in combined

    def test_extract_and_chunk_txt_file(self, tmp_path: Path):
        """Test the full extract_and_chunk flow for a .txt file."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text("Line one content here.\n\nLine two content here.\n\n" * 10)

        chunks = extract_and_chunk(
            file_path=txt_file, file_type="text",
            document_id=42, document_name="sample.txt",
            chunk_size=100, chunk_overlap=20,
        )
        assert len(chunks) > 0
        assert chunks[0].document_id == 42
        assert chunks[0].page_number is None  # txt has no pages

    def test_extract_and_chunk_rejects_unsupported_type(self, tmp_path: Path):
        fake_file = tmp_path / "image.png"
        fake_file.write_bytes(b"fake image data")

        with pytest.raises(ValueError, match="Cannot extract text"):
            extract_and_chunk(fake_file, "image", 1, "image.png")


# ─── Vector Store Unit Tests (in-memory Qdrant) ──────────────────

class TestVectorStore:
    """Tests for the Qdrant vector store wrapper using in-memory mode."""

    @pytest.fixture
    def store(self) -> VectorStore:
        client = QdrantClient(":memory:")
        return VectorStore(client=client, collection_name="test_rag")

    def _fake_embeddings(self, n: int) -> list[list[float]]:
        rng = np.random.RandomState(42)
        return [rng.rand(1536).tolist() for _ in range(n)]

    def test_upsert_and_search(self, store: VectorStore):
        chunks = [
            DocumentChunk(text="Company leave policy allows 20 days.", document_id=1,
                         document_name="policy.pdf", chunk_index=0, page_number=1),
            DocumentChunk(text="Revenue increased by 15% in Q3.", document_id=2,
                         document_name="finance.pdf", chunk_index=0, page_number=3),
        ]
        embeddings = self._fake_embeddings(2)
        store.upsert_chunks(chunks, embeddings, user_id=1)

        # Search with first embedding (should match itself best)
        results = store.search(embeddings[0], user_id=1, top_k=2)
        assert len(results) == 2
        assert results[0]["document_name"] == "policy.pdf"
        assert results[0]["score"] >= results[1]["score"]

    def test_search_filters_by_user_id(self, store: VectorStore):
        chunks = [
            DocumentChunk(text="User 1 data", document_id=1,
                         document_name="u1.txt", chunk_index=0),
            DocumentChunk(text="User 2 data", document_id=2,
                         document_name="u2.txt", chunk_index=0),
        ]
        embeddings = self._fake_embeddings(2)
        store.upsert_chunks(chunks[:1], embeddings[:1], user_id=1)
        store.upsert_chunks(chunks[1:], embeddings[1:], user_id=2)

        # User 1 should only see their own chunks
        results = store.search(embeddings[0], user_id=1, top_k=10)
        assert len(results) == 1
        assert results[0]["document_name"] == "u1.txt"

    def test_delete_by_document(self, store: VectorStore):
        chunks = [
            DocumentChunk(text="Chunk A", document_id=1, document_name="a.txt", chunk_index=0),
            DocumentChunk(text="Chunk B", document_id=1, document_name="a.txt", chunk_index=1),
        ]
        embeddings = self._fake_embeddings(2)
        store.upsert_chunks(chunks, embeddings, user_id=1)

        assert store.count_chunks(document_id=1, user_id=1) == 2
        store.delete_by_document(document_id=1, user_id=1)
        assert store.count_chunks(document_id=1, user_id=1) == 0


# ─── Full Endpoint Integration Tests (mocked embeddings + LLM) ───

def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
    """Deterministic fake embeddings for testing (based on text hash)."""
    rng = np.random.RandomState(42)
    return [rng.rand(1536).tolist() for _ in texts]


def _fake_embed_query(query: str) -> list[float]:
    rng = np.random.RandomState(42)
    return rng.rand(1536).tolist()


@pytest.mark.asyncio
async def test_ingest_txt_document(client: AsyncClient, auth_headers: dict):
    """Upload and ingest a .txt document — mocked embeddings, in-memory Qdrant."""
    content = "The company vacation policy grants 20 days per year.\n" * 5

    with patch("app.services.rag_service.EmbeddingService") as MockEmbedding, \
         patch("app.services.rag_service.VectorStore") as MockStore:
        mock_embed_instance = MockEmbedding.return_value
        mock_embed_instance.embed_texts = AsyncMock(return_value=_fake_embed_texts(["x"] * 5))

        mock_store_instance = MockStore.return_value
        mock_store_instance.upsert_chunks = lambda *a, **kw: len(a[0]) if a else 0

        response = await client.post(
            "/api/v1/rag/ingest",
            files={"file": ("policy.txt", io.BytesIO(content.encode()), "text/plain")},
            headers=auth_headers,
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "policy.txt"
    assert data["file_type"] == "text"
    assert data["embedding_status"] == "completed"
    assert data["chunk_count"] > 0


@pytest.mark.asyncio
async def test_ingest_rejects_csv(client: AsyncClient, auth_headers: dict):
    """CSV files should be rejected for RAG ingestion."""
    response = await client.post(
        "/api/v1/rag/ingest",
        files={"file": ("data.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_rejects_empty_file(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/rag/ingest",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_query_returns_answer_with_sources(client: AsyncClient, auth_headers: dict):
    """Full query flow: embed question → search → LLM answer with citations."""
    # First ingest a document
    content = "Employees receive 20 vacation days annually. " * 10

    with patch("app.services.rag_service.EmbeddingService") as MockEmbedding, \
         patch("app.services.rag_service.VectorStore") as MockStore:
        mock_embed_instance = MockEmbedding.return_value
        mock_embed_instance.embed_texts = AsyncMock(return_value=_fake_embed_texts(["x"] * 10))
        mock_store_instance = MockStore.return_value
        mock_store_instance.upsert_chunks = lambda *a, **kw: len(a[0]) if a else 0

        await client.post(
            "/api/v1/rag/ingest",
            files={"file": ("hr_policy.txt", io.BytesIO(content.encode()), "text/plain")},
            headers=auth_headers,
        )

    # Now query with mocked embedding + search + LLM
    mock_search_results = [
        {"text": "Employees receive 20 vacation days annually.", "document_id": 1,
         "document_name": "hr_policy.txt", "page_number": None, "chunk_index": 0, "score": 0.95},
    ]

    with patch("app.services.rag_service.EmbeddingService") as MockEmbed2, \
         patch("app.services.rag_service.VectorStore") as MockStore2, \
         patch("app.services.rag_service.LLMService") as MockLLM:
        mock_embed2 = MockEmbed2.return_value
        mock_embed2.embed_query = AsyncMock(return_value=_fake_embed_query(""))

        mock_store2 = MockStore2.return_value
        mock_store2.search = lambda *a, **kw: mock_search_results
        mock_store2.ensure_collection = lambda: None

        mock_llm = MockLLM.return_value
        mock_llm.complete = AsyncMock(
            return_value="According to the HR policy, employees get 20 vacation days per year [1]."
        )

        response = await client.post(
            "/api/v1/rag/query",
            json={"question": "How many vacation days do employees get?"},
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "20" in data["answer"]
    assert "[1]" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_name"] == "hr_policy.txt"
    assert data["sources"][0]["source_number"] == 1


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers: dict):
    """List endpoint returns ingested documents."""
    content = "Some test content. " * 10

    with patch("app.services.rag_service.EmbeddingService") as MockEmbed, \
         patch("app.services.rag_service.VectorStore") as MockStore:
        mock_embed = MockEmbed.return_value
        mock_embed.embed_texts = AsyncMock(return_value=_fake_embed_texts(["x"] * 5))
        mock_store = MockStore.return_value
        mock_store.upsert_chunks = lambda *a, **kw: 0

        await client.post(
            "/api/v1/rag/ingest",
            files={"file": ("doc1.txt", io.BytesIO(content.encode()), "text/plain")},
            headers=auth_headers,
        )

    response = await client.get("/api/v1/rag/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(d["name"] == "doc1.txt" for d in data["documents"])


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers: dict):
    """Delete removes document from DB (and would remove from Qdrant in real use)."""
    content = "Delete me content. " * 10

    with patch("app.services.rag_service.EmbeddingService") as MockEmbed, \
         patch("app.services.rag_service.VectorStore") as MockStore:
        mock_embed = MockEmbed.return_value
        mock_embed.embed_texts = AsyncMock(return_value=_fake_embed_texts(["x"] * 5))
        mock_store = MockStore.return_value
        mock_store.upsert_chunks = lambda *a, **kw: 0

        ingest_resp = await client.post(
            "/api/v1/rag/ingest",
            files={"file": ("to_delete.txt", io.BytesIO(content.encode()), "text/plain")},
            headers=auth_headers,
        )
    doc_id = ingest_resp.json()["id"]

    with patch("app.services.rag_service.VectorStore") as MockStore2:
        mock_store2 = MockStore2.return_value
        mock_store2.delete_by_document = lambda *a, **kw: None
        mock_store2.ensure_collection = lambda: None

        delete_resp = await client.delete(f"/api/v1/rag/documents/{doc_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    # Verify gone from list
    list_resp = await client.get("/api/v1/rag/documents", headers=auth_headers)
    doc_ids = [d["id"] for d in list_resp.json()["documents"]]
    assert doc_id not in doc_ids


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/api/v1/rag/documents/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rag_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/rag/query", json={"question": "test"})
    assert response.status_code == 401
