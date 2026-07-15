"""
SQL Query Log ORM Model

Audit trail for every natural-language-to-SQL query executed on the platform.

Why log every query?
- Debugging: When the LLM generates bad SQL, we need to see exactly what
  it produced and why it failed.
- Dashboard: "Recent queries" widget on the user dashboard (Phase 9).
- Trust/safety: An auditable record of every query run against user data —
  important once this handles real business data.
- Product analytics: Understanding what kinds of questions users actually
  ask helps prioritize future NL2SQL improvements.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SQLQueryLog(Base):
    __tablename__ = "sql_query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)  # Original NL question
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM-generated SQL (null if generation failed)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM's natural-language summary of results

    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Rows returned (null if failed)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # Populated if success=False

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="sql_query_logs")
    dataset = relationship("Dataset", backref="sql_query_logs")
