"""
Report ORM Model

Represents AI-generated reports (executive summaries, analyses, recommendations).
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)  # executive_summary, sales_analysis, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown/HTML content
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)  # Charts, KPIs, sources
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="reports")
