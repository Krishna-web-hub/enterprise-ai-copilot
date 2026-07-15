"""
Report Generation Service

Generates AI-powered business reports using the LLM, optionally grounded
in dataset KPIs computed by KPIService.

Report types (from the spec):
- executive_summary: High-level business overview with key findings
- sales_analysis: Revenue/sales trends, top performers, growth metrics
- customer_insights: Segmentation, behavior patterns, retention analysis
- anomaly_report: Unusual patterns, outliers, potential issues
- forecast_report: Projected trends and predictions
- recommendation_report: Actionable recommendations based on data

Pipeline:
1. If a dataset_id is provided, compute KPIs to ground the report in real data
2. Build a report-type-specific prompt with the KPI context
3. Call the LLM to generate markdown content
4. Save the Report record to the database
5. Return the completed report
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.services.data_service import DataService
from app.services.kpi_service import KPIService, KPIServiceError
from app.services.llm_service import LLMService, LLMServiceError


class ReportServiceError(Exception):
    pass


# ─── Report-type-specific system prompts ───────────────────────

REPORT_PROMPTS = {
    "executive_summary": """You are a senior business consultant writing an executive summary for C-level stakeholders.
Write a concise, data-driven executive summary in markdown format.
Include: Key Findings, Business Health Indicators, Risks, and Next Steps.
Use bullet points for clarity. Keep it to 1-2 pages equivalent.""",

    "sales_analysis": """You are a sales analytics expert writing a sales performance report.
Write a detailed sales analysis in markdown format.
Include: Revenue Overview, Top Products/Categories, Growth Trends, Underperformers, and Opportunities.
Use specific numbers from the data provided. Include suggestions for improvement.""",

    "customer_insights": """You are a customer analytics specialist writing a customer behavior report.
Write a customer insights report in markdown format.
Include: Customer Segments, Behavior Patterns, Retention Indicators, High-Value Customers, and Engagement Recommendations.
Focus on actionable insights that can improve customer relationships.""",

    "anomaly_report": """You are a data quality and risk analyst writing an anomaly detection report.
Write an anomaly/risk report in markdown format.
Include: Detected Anomalies, Severity Assessment, Potential Root Causes, Impact Analysis, and Recommended Actions.
Flag anything unusual in the data patterns that warrants attention.""",

    "forecast_report": """You are a business forecasting analyst writing a predictive outlook report.
Write a forecast report in markdown format.
Include: Current Trends, Projected Growth/Decline, Key Assumptions, Confidence Levels, and Scenario Analysis (best/worst/likely).
Base forecasts on the patterns visible in the provided data.""",

    "recommendation_report": """You are a strategic business advisor writing an action plan.
Write a recommendations report in markdown format.
Include: Priority Actions (High/Medium/Low), Expected Impact, Resource Requirements, Timeline, and Success Metrics.
Make recommendations specific, measurable, and actionable based on the data insights.""",
}

REPORT_TITLES = {
    "executive_summary": "Executive Summary",
    "sales_analysis": "Sales Performance Analysis",
    "customer_insights": "Customer Insights Report",
    "anomaly_report": "Anomaly & Risk Report",
    "forecast_report": "Forecast & Outlook Report",
    "recommendation_report": "Recommendations & Action Plan",
}


class ReportService:
    """Generates and manages AI-powered business reports."""

    def __init__(self, db: AsyncSession, llm: Optional[LLMService] = None):
        self.db = db
        self.llm = llm or LLMService()

    async def generate_report(
        self,
        user_id: int,
        report_type: str,
        dataset_id: Optional[int] = None,
        additional_context: Optional[str] = None,
    ) -> Report:
        """
        Generate an AI-powered business report.

        Args:
            user_id: Report owner
            report_type: One of the 6 supported report types
            dataset_id: Optional dataset to ground the report in real data
            additional_context: Optional extra instructions for the AI

        Returns:
            Saved Report record with generated markdown content
        """
        if report_type not in REPORT_PROMPTS:
            raise ReportServiceError(f"Unknown report type: {report_type}")

        # Build context from dataset KPIs (if dataset provided)
        data_context = ""
        dataset_name = "General"

        if dataset_id:
            data_service = DataService(self.db)
            dataset = await data_service.get_dataset(dataset_id, user_id)
            if not dataset:
                raise ReportServiceError(f"Dataset {dataset_id} not found")

            dataset_name = dataset.name

            try:
                kpi_service = KPIService()
                kpis = kpi_service.compute_kpis(dataset)
                data_context = self._format_kpi_context(kpis)
            except KPIServiceError:
                data_context = f"Dataset: {dataset.name} ({dataset.row_count} rows, {dataset.column_count} columns)"

        # Build the LLM prompt
        system_prompt = REPORT_PROMPTS[report_type]
        user_prompt = self._build_user_prompt(data_context, additional_context)

        # Generate the report content
        try:
            content = await self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.4,  # Slightly creative but still grounded
            )
        except LLMServiceError as e:
            raise ReportServiceError(f"Report generation failed: {str(e)}") from e

        # Build title
        title = f"{REPORT_TITLES[report_type]} — {dataset_name}"

        # Save to database
        report = Report(
            user_id=user_id,
            title=title,
            report_type=report_type,
            content=content,
            metadata_={
                "dataset_id": dataset_id,
                "dataset_name": dataset_name if dataset_id else None,
                "additional_context": additional_context,
            },
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def list_reports(self, user_id: int) -> list[Report]:
        """List all reports for a user, newest first."""
        result = await self.db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_report(self, report_id: int, user_id: int) -> Optional[Report]:
        """Get a single report owned by the user."""
        result = await self.db.execute(
            select(Report).where(Report.id == report_id, Report.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete_report(self, report_id: int, user_id: int) -> bool:
        """Delete a report. Returns True if found and deleted."""
        report = await self.get_report(report_id, user_id)
        if not report:
            return False
        await self.db.delete(report)
        return True

    # ─── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _format_kpi_context(kpis: dict) -> str:
        """Format KPI computation results into a text context for the LLM prompt."""
        parts = [f"Dataset: {kpis['dataset_name']} ({kpis['row_count']} rows)"]

        if kpis.get("summary_kpis"):
            parts.append("\nKey Metrics:")
            for kpi in kpis["summary_kpis"]:
                parts.append(f"  - {kpi['name']}: {kpi['value']}")

        if kpis.get("numeric_stats"):
            parts.append("\nNumeric Column Statistics:")
            for stat in kpis["numeric_stats"][:5]:
                parts.append(
                    f"  - {stat['column']}: sum={stat['sum']}, avg={stat['mean']}, "
                    f"min={stat['min']}, max={stat['max']}"
                )

        if kpis.get("category_breakdowns"):
            parts.append("\nCategory Distributions:")
            for cat in kpis["category_breakdowns"][:3]:
                values_str = ", ".join(
                    f"{v['value']} ({v['percent']}%)" for v in cat["top_values"][:5]
                )
                parts.append(f"  - {cat['column']}: {values_str}")

        if kpis.get("time_trends"):
            parts.append("\nTime Trends (monthly):")
            for trend in kpis["time_trends"][-6:]:
                metrics_str = ", ".join(f"{k}={v}" for k, v in trend["metrics"].items())
                parts.append(f"  - {trend['period']}: {metrics_str}")

        return "\n".join(parts)

    @staticmethod
    def _build_user_prompt(data_context: str, additional_context: Optional[str]) -> str:
        """Build the user prompt from available context."""
        parts = []

        if data_context:
            parts.append(f"Data Context:\n{data_context}")

        if additional_context:
            parts.append(f"\nAdditional Instructions:\n{additional_context}")

        if not parts:
            parts.append(
                "Generate this report based on general business best practices. "
                "No specific dataset is provided — write a template-style report "
                "that demonstrates the format and structure."
            )

        parts.append("\nPlease generate the report now in markdown format.")
        return "\n\n".join(parts)
