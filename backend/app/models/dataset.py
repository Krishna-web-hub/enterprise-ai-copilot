"""
Dataset ORM Model

Represents an uploaded dataset (CSV, Excel, JSON, etc.).
Stores metadata about the file and its structure.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv, xlsx, json, pdf, docx, image
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL for unstructured files
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    columns_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {name, dtype, nulls, sample}
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="datasets")
