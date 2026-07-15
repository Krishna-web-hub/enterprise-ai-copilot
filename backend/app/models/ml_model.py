"""
ML Model ORM

Represents a trained machine learning model with its metrics and configuration.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)  # classification, regression, clustering
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)  # xgboost, random_forest, etc.
    # Nullable because clustering/anomaly_detection are unsupervised — there is no target label.
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    feature_columns: Mapped[list] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)  # accuracy, f1, rmse, etc.
    feature_importance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_path: Mapped[str] = mapped_column(Text, nullable=False)  # Path to saved model file
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Hyperparameters used
    training_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="ml_models")
    dataset = relationship("Dataset", backref="ml_models")
