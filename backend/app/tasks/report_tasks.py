"""
Report Generation Background Task

Wraps ReportService.generate_report() as a Celery task. Report generation
calls the LLM (which can take 5-15 seconds), so running it in the background
keeps the API responsive for other users.
"""

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="reports.generate_report", max_retries=1)
def generate_report_task(self, user_id: int, report_type: str,
                         dataset_id: int | None, additional_context: str | None) -> dict:
    """
    Background task: Generate an AI-powered report.
    
    Returns a JSON-serializable dict with the report info.
    """
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.services.report_service import ReportService, ReportServiceError

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            try:
                report_service = ReportService(db)
                report = await report_service.generate_report(
                    user_id=user_id,
                    report_type=report_type,
                    dataset_id=dataset_id,
                    additional_context=additional_context,
                )
                await db.commit()

                return {
                    "success": True,
                    "report_id": report.id,
                    "title": report.title,
                    "report_type": report.report_type,
                }
            except ReportServiceError as e:
                return {"success": False, "error": str(e)}
            except Exception as e:
                return {"success": False, "error": f"Unexpected error: {str(e)}"}

    return asyncio.run(_run())
