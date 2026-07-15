"""
Reports, Dashboard & Power BI Endpoints

Routes:
- GET  /dashboard       → Dashboard summary (counts, recent activity)
- POST /kpis            → Compute KPIs for a dataset
- POST /powerbi/export  → Export dataset with KPIs in Excel/CSV format
- POST /generate        → Generate AI report (Phase 10 — stub)
- GET  /reports         → List reports (Phase 10 — stub)
- GET  /reports/{id}    → Get a report (Phase 10 — stub)
"""

import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.chat import ChatSession
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.ml_model import MLModel
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import (
    DashboardResponse,
    KPIRequest,
    KPIResponse,
    PowerBIExportRequest,
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
)
from app.services.data_service import DataService
from app.services.kpi_service import KPIService, KPIServiceError
from app.services.report_service import ReportService, ReportServiceError

router = APIRouter()


# ─── Dashboard ─────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard summary data.

    Returns counts of all user resources and recent activity.
    Cached for 60 seconds per user to reduce DB load.
    """
    uid = current_user.id

    # Try cache first
    cached = await cache.get("dashboard", uid)
    if cached:
        return DashboardResponse(**cached)

    # Cache miss — compute from DB
    ds_count = (await db.execute(select(func.count(Dataset.id)).where(Dataset.user_id == uid))).scalar() or 0
    model_count = (await db.execute(select(func.count(MLModel.id)).where(MLModel.user_id == uid))).scalar() or 0
    report_count = (await db.execute(select(func.count(Report.id)).where(Report.user_id == uid))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)).where(Document.user_id == uid))).scalar() or 0
    chat_count = (await db.execute(select(func.count(ChatSession.id)).where(ChatSession.user_id == uid))).scalar() or 0

    chats_result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == uid).order_by(ChatSession.created_at.desc()).limit(5)
    )
    recent_chats = [
        {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()}
        for s in chats_result.scalars().all()
    ]

    ds_result = await db.execute(
        select(Dataset).where(Dataset.user_id == uid).order_by(Dataset.created_at.desc()).limit(5)
    )
    recent_datasets = [
        {"id": d.id, "name": d.name, "file_type": d.file_type, "created_at": d.created_at.isoformat()}
        for d in ds_result.scalars().all()
    ]

    result = {
        "total_datasets": ds_count,
        "total_models": model_count,
        "total_reports": report_count,
        "total_documents": doc_count,
        "total_chat_sessions": chat_count,
        "recent_chats": recent_chats,
        "recent_datasets": recent_datasets,
    }

    # Store in cache (60s TTL)
    await cache.set("dashboard", uid, result, ttl=60)

    return DashboardResponse(**result)


# ─── KPIs ──────────────────────────────────────────────────────

@router.post("/kpis", response_model=KPIResponse)
async def compute_kpis(
    request: KPIRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compute auto-detected business KPIs for a dataset.

    Cached for 5 minutes per dataset (KPIs are expensive to compute
    and datasets don't change after upload).
    """
    uid = current_user.id
    cache_key = f"kpis:{request.dataset_id}"

    # Try cache first
    cached = await cache.get(cache_key, uid)
    if cached:
        return KPIResponse(**cached)

    data_service = DataService(db)
    dataset = await data_service.get_dataset(request.dataset_id, uid)

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    kpi_service = KPIService()
    try:
        result = kpi_service.compute_kpis(dataset)
    except KPIServiceError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Cache for 5 minutes
    await cache.set(cache_key, uid, result, ttl=300)

    return KPIResponse(**result)


# ─── Power BI Export ───────────────────────────────────────────

@router.post("/powerbi/export")
async def export_for_powerbi(
    request: PowerBIExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export a dataset with computed KPIs in Power BI-ready format.

    Formats:
    - excel: Multi-sheet Excel workbook (raw data + summary + stats + category breakdown)
    - csv: Raw data as CSV (simpler, compatible with any tool)

    The Excel format is designed for direct import into Power BI Desktop,
    with pre-computed KPI sheets ready for dashboard creation.
    """
    data_service = DataService(db)
    dataset = await data_service.get_dataset(request.dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    kpi_service = KPIService()

    try:
        export_data = kpi_service.generate_export_data(dataset)
    except KPIServiceError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if request.format == "csv":
        # Simple CSV export of raw data
        buffer = io.StringIO()
        export_data["raw_data"].to_csv(buffer, index=False)
        content = buffer.getvalue().encode("utf-8")

        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{dataset.name}_export.csv"'},
        )
    else:
        # Multi-sheet Excel export
        buffer = io.BytesIO()
        with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
            export_data["raw_data"].to_excel(writer, sheet_name="Raw Data", index=False)
            export_data["summary"].to_excel(writer, sheet_name="Summary KPIs", index=False)
            if not export_data["numeric_stats"].empty:
                export_data["numeric_stats"].to_excel(writer, sheet_name="Numeric Stats", index=False)
            if not export_data["category_breakdown"].empty:
                export_data["category_breakdown"].to_excel(writer, sheet_name="Categories", index=False)

        buffer.seek(0)
        filename = dataset.name.rsplit(".", 1)[0] + "_powerbi.xlsx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )



# ─── Report Generation & Retrieval (Phase 10) ─────────────────

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerateRequest,
    run_async: bool = Query(False, alias="async", description="Run in background"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI-powered business report.

    Add ?async=true to run in background (returns task_id for polling).
    """
    if run_async:
        try:
            from app.tasks.report_tasks import generate_report_task
            task = generate_report_task.delay(
                user_id=current_user.id,
                report_type=request.report_type,
                dataset_id=request.dataset_id,
                additional_context=request.additional_context,
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"task_id": task.id, "status": "PENDING", "message": "Report generation started. Poll GET /api/v1/tasks/{task_id} for status."},
            )
        except Exception:
            # Redis/Celery not available — fall back to sync
            pass

    report_service = ReportService(db)

    try:
        report = await report_service.generate_report(
            user_id=current_user.id,
            report_type=request.report_type,
            dataset_id=request.dataset_id,
            additional_context=request.additional_context,
        )
    except ReportServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return ReportResponse.from_orm_report(report)


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reports generated by the current user, newest first."""
    report_service = ReportService(db)
    reports = await report_service.list_reports(current_user.id)
    return ReportListResponse(
        reports=[ReportResponse.from_orm_report(r) for r in reports],
        total=len(reports),
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific report by ID."""
    report_service = ReportService(db)
    report = await report_service.get_report(report_id, current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    return ReportResponse.from_orm_report(report)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a generated report."""
    report_service = ReportService(db)
    deleted = await report_service.delete_report(report_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
