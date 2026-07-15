"""
RAG Ingestion Background Task

Wraps RAGService.ingest_document() as a Celery task. Document chunking +
embedding generation can take 5-30 seconds for large PDFs, so running it
in the background keeps the API responsive.
"""

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="rag.ingest_document", max_retries=1)
def ingest_document_task(self, user_id: int, document_id: int) -> dict:
    """
    Background task: Ingest a document for RAG (chunk, embed, store).
    
    Returns a JSON-serializable dict with the document status.
    """
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.models.document import Document
    from app.services.rag_service import RAGService, RAGServiceError

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(Document).where(Document.id == document_id, Document.user_id == user_id)
                )
                document = result.scalar_one_or_none()
                if not document:
                    return {"success": False, "error": f"Document {document_id} not found"}

                rag_service = RAGService(db)
                document = await rag_service.ingest_document(document, user_id)
                await db.commit()

                return {
                    "success": True,
                    "document_id": document.id,
                    "name": document.name,
                    "embedding_status": document.embedding_status,
                    "chunk_count": document.chunk_count,
                }
            except RAGServiceError as e:
                return {"success": False, "error": str(e)}
            except Exception as e:
                return {"success": False, "error": f"Unexpected error: {str(e)}"}

    return asyncio.run(_run())
