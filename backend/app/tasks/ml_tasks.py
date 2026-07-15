"""
ML Training Background Task

Wraps MLService.train() as a Celery task so it runs in a background worker
instead of blocking the API request. The API endpoint returns a task_id
immediately (202 Accepted), and the frontend polls for completion.

Why a wrapper instead of making MLService itself a Celery task?
- Separation of concerns: MLService is pure business logic (testable without Celery).
  The task is just the async dispatch layer.
- Celery tasks must accept JSON-serializable arguments (no ORM objects, no DB sessions).
  The task receives primitive IDs and reconstructs what it needs inside the worker.
"""

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="ml.train_model", max_retries=0)
def train_model_task(self, user_id: int, dataset_id: int, model_type: str,
                     target_column: str | None, algorithm: str | None,
                     feature_columns: list[str] | None, name: str | None) -> dict:
    """
    Background task: Train an ML model.
    
    Runs synchronously inside the Celery worker (which has its own process/thread).
    Returns a JSON-serializable dict with the trained model info.
    """
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.models.dataset import Dataset
    from app.services.data_service import DataService
    from app.services.ml_service import MLService, MLServiceError

    # Celery workers need their own DB engine (not shared with the API process)
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            try:
                data_service = DataService(db)
                dataset = await data_service.get_dataset(dataset_id, user_id)
                if not dataset:
                    return {"success": False, "error": f"Dataset {dataset_id} not found"}

                ml_service = MLService(db)
                ml_model = await ml_service.train(
                    dataset=dataset,
                    user_id=user_id,
                    model_type=model_type,
                    target_column=target_column,
                    algorithm=algorithm,
                    feature_columns=feature_columns,
                    name=name,
                )
                await db.commit()

                return {
                    "success": True,
                    "model_id": ml_model.id,
                    "name": ml_model.name,
                    "algorithm": ml_model.algorithm,
                    "metrics": ml_model.metrics,
                    "feature_importance": ml_model.feature_importance,
                    "training_duration_seconds": ml_model.training_duration_seconds,
                }
            except MLServiceError as e:
                return {"success": False, "error": str(e)}
            except Exception as e:
                return {"success": False, "error": f"Unexpected error: {str(e)}"}

    return asyncio.run(_run())
