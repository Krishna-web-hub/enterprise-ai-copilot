"""
Data Management Schemas (Pydantic)

Defines request/response shapes for file upload and dataset operations.

These schemas serve as the API contract between frontend and backend:
- DatasetResponse: What clients receive for a single dataset
- DatasetListResponse: Paginated list with total count
- DatasetPreviewResponse: First N rows of structured data
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ColumnMetadata(BaseModel):
    """Metadata about a single column in a structured dataset."""
    name: str
    dtype: str
    null_count: int
    null_percent: float
    unique_count: int
    sample_values: list[str]


class DatasetResponse(BaseModel):
    """
    Single dataset details returned by the API.

    This is what the frontend receives after upload or when fetching a dataset.
    Note: file_path is NOT exposed — that's an internal detail.
    """
    id: int
    name: str
    file_type: str
    file_size_bytes: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns_metadata: Optional[list[ColumnMetadata]] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Paginated list of datasets."""
    datasets: list[DatasetResponse]
    total: int
    skip: int
    limit: int


class DatasetPreviewResponse(BaseModel):
    """
    Preview of the first N rows of a structured dataset.

    Used by the frontend to render a data table without
    downloading the entire file.
    """
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    preview_rows: int
    dtypes: dict[str, str]
    message: Optional[str] = None


class DatasetDeleteResponse(BaseModel):
    """Confirmation of dataset deletion."""
    message: str
    dataset_id: int
