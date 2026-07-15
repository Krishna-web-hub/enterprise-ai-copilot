"""
Machine Learning Schemas (Pydantic)

Defines request/response shapes for ML training, prediction, and model management.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    """
    Request to train a new ML model.

    target_column is required for classification/regression (supervised),
    and must be omitted for clustering/anomaly_detection (unsupervised —
    there is no label to predict, only patterns to discover).
    """
    dataset_id: int
    model_type: str = Field(..., pattern="^(classification|regression|clustering|anomaly_detection)$")
    target_column: Optional[str] = None
    algorithm: Optional[str] = None  # If None, system auto-selects best algorithm
    feature_columns: Optional[list[str]] = None  # If None, system uses all except target
    name: Optional[str] = None  # User-friendly model name


class TrainResponse(BaseModel):
    """Response after model training completes."""
    id: int
    name: str
    model_type: str
    algorithm: str
    metrics: dict  # accuracy, f1, rmse, etc.
    feature_importance: Optional[dict] = None
    training_duration_seconds: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    """Request to make predictions using a trained model."""
    model_id: int
    input_data: dict | list[dict]  # Single record or batch


class PredictResponse(BaseModel):
    """Prediction results with explanation."""
    predictions: list[dict]  # [{prediction, confidence, explanation}]
    model_id: int
    model_name: str


class ModelSummary(BaseModel):
    """Brief model info for list views."""
    id: int
    name: str
    model_type: str
    algorithm: str
    metrics: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    """List of trained models."""
    models: list[ModelSummary]
    total: int


class ModelDetailResponse(BaseModel):
    """Full model details including feature importance."""
    id: int
    name: str
    model_type: str
    algorithm: str
    target_column: Optional[str] = None
    feature_columns: list[str]
    metrics: dict
    feature_importance: Optional[dict] = None
    parameters: Optional[dict] = None
    training_duration_seconds: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
