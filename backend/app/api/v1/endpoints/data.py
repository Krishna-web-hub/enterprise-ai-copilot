"""
Data Management Endpoints

Handles file uploads, dataset listing, preview, and deletion.
Supports CSV, Excel, JSON, PDF, Word, and images.

Architecture:
- Thin route handlers that delegate to DataService
- Each handler: validate input → call service → format response
- Authentication enforced via get_current_user dependency

Routes:
- POST /upload              → Upload a file/dataset
- GET  /datasets            → List user's datasets (paginated)
- GET  /datasets/{id}       → Get dataset details with column metadata
- GET  /datasets/{id}/preview → Get first N rows as table data
- DELETE /datasets/{id}     → Delete a dataset and its file
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.data import (
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetPreviewResponse,
    DatasetResponse,
)
from app.services.data_service import DataService

router = APIRouter()


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a data file for analysis.

    Supported formats:
    - Structured: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)
    - Documents: PDF (.pdf), Word (.docx, .doc), Text (.txt)
    - Images: PNG, JPG, JPEG, GIF

    For structured files, the system automatically extracts:
    - Row and column counts
    - Column names and data types
    - Null value statistics
    - Sample values per column

    Maximum file size: 100MB (configurable via MAX_UPLOAD_SIZE_MB).
    """
    service = DataService(db)

    try:
        dataset = await service.upload_file(file, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Invalidate dashboard cache (counts changed)
    await cache.delete("dashboard", current_user.id)

    return dataset


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all datasets uploaded by the current user.

    Supports pagination:
    - skip: offset (default 0)
    - limit: page size (default 20, max 100)

    Returns datasets ordered by newest first.
    """
    service = DataService(db)
    datasets, total = await service.list_datasets(current_user.id, skip=skip, limit=limit)

    return DatasetListResponse(
        datasets=datasets,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed info about a specific dataset.

    Returns column metadata including types, null counts, and sample values.
    Only returns datasets owned by the authenticated user.
    """
    service = DataService(db)
    dataset = await service.get_dataset(dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    return dataset


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(
    dataset_id: int,
    rows: int = Query(50, ge=1, le=500, description="Number of rows to preview"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a preview of the first N rows of a structured dataset.

    Returns:
    - Column names
    - Row data as a 2D array (for efficient table rendering)
    - Data types per column
    - Total row count vs preview row count

    Only works for structured files (CSV, Excel, JSON).
    For unstructured files, returns an empty result with an explanatory message.
    """
    service = DataService(db)
    dataset = await service.get_dataset(dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    try:
        preview = service.get_preview(dataset, num_rows=rows)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file not found on disk. It may have been moved or deleted.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse dataset: {str(e)}",
        )

    return DatasetPreviewResponse(**preview)


@router.delete("/datasets/{dataset_id}", response_model=DatasetDeleteResponse)
async def delete_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a dataset and its associated file from disk.

    This is irreversible — the file and all metadata are permanently removed.
    Only the dataset owner can delete it.
    """
    service = DataService(db)
    deleted = await service.delete_dataset(dataset_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Invalidate dashboard cache (counts changed)
    await cache.delete("dashboard", current_user.id)

    return DatasetDeleteResponse(
        message="Dataset deleted successfully",
        dataset_id=dataset_id,
    )

    # Note: cache invalidation happens above via the return — but we need it BEFORE return.
    # Let me fix the placement.


@router.get("/datasets/{dataset_id}/analytics")
async def get_dataset_analytics(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate comprehensive analytics for a dataset.

    Returns:
    - summary: row count, column count, memory usage, data quality score
    - columns: per-column stats (mean, median, std, min, max, distribution, top values)
    - correlations: numeric column correlation matrix
    - null_analysis: missing value summary per column
    - data_types: breakdown of column types (numeric, categorical, datetime)
    """
    import numpy as np
    import pandas as pd
    from pathlib import Path
    from app.core.config import settings

    service = DataService(db)
    dataset = await service.get_dataset(dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.file_type not in ("csv", "excel", "json"):
        raise HTTPException(status_code=422, detail="Analytics only available for structured datasets (CSV, Excel, JSON)")

    # Resolve file path
    file_path = Path(dataset.file_path)
    if not file_path.exists():
        file_path = Path(settings.upload_path) / dataset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found on disk")

    # Read data (limit to 50k rows for performance)
    from app.utils.file_readers import read_structured_file
    df = read_structured_file(file_path, dataset.file_type)
    if len(df) > 50000:
        df = df.sample(50000, random_state=42)

    # ─── Summary ──────────────────────────────────────────────
    total_cells = df.shape[0] * df.shape[1]
    total_nulls = int(df.isna().sum().sum())
    data_quality = round((1 - total_nulls / max(total_cells, 1)) * 100, 1)

    summary = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "total_cells": total_cells,
        "total_nulls": total_nulls,
        "data_quality_percent": data_quality,
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    # ─── Column Analytics ─────────────────────────────────────
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    columns_analytics = []

    for col in df.columns:
        series = df[col]
        col_info: dict = {
            "name": col,
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "null_percent": round(series.isna().sum() / len(df) * 100, 2),
            "unique_count": int(series.nunique()),
            "unique_percent": round(series.nunique() / max(len(df), 1) * 100, 2),
        }

        if col in numeric_cols:
            col_info["type"] = "numeric"
            desc = series.describe()
            col_info["stats"] = {
                "mean": round(float(desc.get("mean", 0)), 4),
                "median": round(float(series.median()), 4) if not series.isna().all() else None,
                "std": round(float(desc.get("std", 0)), 4),
                "min": float(desc.get("min", 0)),
                "max": float(desc.get("max", 0)),
                "q25": float(desc.get("25%", 0)),
                "q75": float(desc.get("75%", 0)),
                "skewness": round(float(series.skew()), 4) if len(series.dropna()) > 2 else 0,
                "kurtosis": round(float(series.kurtosis()), 4) if len(series.dropna()) > 3 else 0,
            }
            # Distribution (histogram bins)
            try:
                clean = series.dropna()
                if len(clean) > 0:
                    counts, edges = np.histogram(clean, bins=min(20, max(5, int(len(clean) ** 0.5))))
                    col_info["distribution"] = {
                        "bins": [round(float(e), 4) for e in edges],
                        "counts": [int(c) for c in counts],
                    }
            except Exception:
                pass

        elif col in categorical_cols:
            col_info["type"] = "categorical"
            # Top values
            top_values = series.value_counts().head(10)
            col_info["top_values"] = [
                {"value": str(v), "count": int(c), "percent": round(c / len(df) * 100, 2)}
                for v, c in top_values.items()
            ]

        elif col in datetime_cols:
            col_info["type"] = "datetime"
            col_info["stats"] = {
                "min": str(series.min()),
                "max": str(series.max()),
                "range_days": (series.max() - series.min()).days if not series.isna().all() else 0,
            }
        else:
            col_info["type"] = "other"

        columns_analytics.append(col_info)

    # ─── Correlations (numeric only) ──────────────────────────
    correlations = None
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        correlations = {
            "columns": numeric_cols,
            "matrix": [[round(float(v), 4) if not pd.isna(v) else 0 for v in row] for row in corr_matrix.values],
        }

    # ─── Data Types Summary ───────────────────────────────────
    data_types = {
        "numeric": len(numeric_cols),
        "categorical": len(categorical_cols),
        "datetime": len(datetime_cols),
        "other": len(df.columns) - len(numeric_cols) - len(categorical_cols) - len(datetime_cols),
    }

    # ─── Null Analysis ────────────────────────────────────────
    null_analysis = []
    for col in df.columns:
        nc = int(df[col].isna().sum())
        if nc > 0:
            null_analysis.append({
                "column": col,
                "null_count": nc,
                "null_percent": round(nc / len(df) * 100, 2),
            })
    null_analysis.sort(key=lambda x: x["null_count"], reverse=True)

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset.name,
        "summary": summary,
        "data_types": data_types,
        "columns": columns_analytics,
        "correlations": correlations,
        "null_analysis": null_analysis,
    }
