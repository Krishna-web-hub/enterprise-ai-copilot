"""
Reports, Dashboard & Power BI Schemas (Pydantic)

Defines request/response shapes for:
- Dashboard summary (Phase 9)
- KPI computation results
- Power BI export requests
- AI-generated reports (Phase 10 — stubs remain for now)
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ─── Dashboard ─────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    """Dashboard summary data returned to the frontend."""
    total_datasets: int
    total_models: int
    total_reports: int
    total_documents: int
    total_chat_sessions: int
    recent_chats: list[dict]
    recent_datasets: list[dict]


# ─── KPIs & Power BI Export ────────────────────────────────────

class KPIRequest(BaseModel):
    """Request to compute KPIs for a dataset."""
    dataset_id: int


class KPISummaryItem(BaseModel):
    name: str
    value: Any
    type: str  # "count", "currency", "number", "percent"


class NumericStatItem(BaseModel):
    column: str
    count: int
    sum: float
    mean: float
    median: float
    std: float
    min: float
    max: float


class CategoryBreakdownItem(BaseModel):
    column: str
    top_values: list[dict]


class KPIResponse(BaseModel):
    """Full KPI computation results for a dataset."""
    dataset_name: str
    row_count: int
    column_count: int
    summary_kpis: list[KPISummaryItem]
    numeric_stats: list[NumericStatItem]
    category_breakdowns: list[CategoryBreakdownItem]
    time_trends: list[dict]


class PowerBIExportRequest(BaseModel):
    """Request to export a dataset in Power BI-ready format."""
    dataset_id: int
    format: str = Field(default="excel", pattern="^(excel|csv)$")


# ─── Reports (Phase 10 — schema ready, implementation later) ──

class ReportGenerateRequest(BaseModel):
    """Request to generate a new AI-powered report."""
    dataset_id: Optional[int] = None
    report_type: str = Field(
        ...,
        pattern="^(executive_summary|sales_analysis|customer_insights|anomaly_report|forecast_report|recommendation_report)$",
    )
    additional_context: Optional[str] = None


class ReportResponse(BaseModel):
    """Generated report details."""
    id: int
    title: str
    report_type: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_report(cls, report) -> "ReportResponse":
        """Create from ORM Report object (handles metadata_ field name)."""
        return cls(
            id=report.id,
            title=report.title,
            report_type=report.report_type,
            content=report.content,
            metadata=report.metadata_,
            created_at=report.created_at,
        )


class ReportListResponse(BaseModel):
    """List of reports."""
    reports: list[ReportResponse]
    total: int
