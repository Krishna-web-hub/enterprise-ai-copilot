"""
Embedding Service

Thin wrapper around OpenAI's text-embedding API with batch support.

Why a wrapper?
- Same provider-independence rationale as LLMService: every RAG component
  depends on THIS module, not on the OpenAI SDK directly. Swapping to a
  local embedding model (e.g. sentence-transformers) later means editing
  one file.
- Batch support: OpenAI allows up to 2048 texts per embedding call. We
  batch chunks to minimize API round-trips during document ingestion.
- Consistent error handling in one place.

Model choice: text-embedding-3-small (1536 dims)
- Cheapest OpenAI embedding model ($0.02/1M tokens)
- Good retrieval quality for most business documents
- 1536 dimensions is a reasonable balance between precision and storage cost
"""

from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings

EMBEDDING_DIMENSION = 1536  # text-embedding-3-small output size
MAX_BATCH_SIZE = 2048  # OpenAI's max texts per request


class EmbeddingServiceError(Exception):
    """Raised when embedding generation fails."""
    pass


class EmbeddingService:
    """Generates dense vector embeddings for text chunks and queries."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise EmbeddingServiceError(
                    "OPENAI_API_KEY is not configured. Set it in your .env file."
                )
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed (each chunk or query)

        Returns:
            List of embedding vectors (each a list of 1536 floats),
            in the same order as the input texts.

        Raises:
            EmbeddingServiceError: If the API call fails
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Process in batches (OpenAI allows up to 2048 texts per call)
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i + MAX_BATCH_SIZE]
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                # Response embeddings are guaranteed to be in input order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except OpenAIError as e:
                raise EmbeddingServiceError(f"Embedding API call failed: {str(e)}") from e

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate an embedding for a single query string.

        Convenience method for retrieval (embeds the user's question).
        """
        results = await self.embed_texts([query])
        return results[0]
