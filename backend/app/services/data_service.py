"""
Data Management Service

Handles file upload processing, dataset metadata extraction, and storage.

Architecture:
- Upload flow: validate → save to disk → parse metadata → store in DB
- Parsing is done eagerly on upload for structured data (CSV, Excel, JSON)
- Unstructured files (PDF, Word, images) store basic file info only
  (content extraction happens later in RAG Phase 7)

Why extract metadata on upload?
- Users immediately see column names, types, row counts
- The ML engine (Phase 5) uses column metadata to suggest algorithms
- The SQL agent (Phase 4) needs column info to generate queries
- Avoids re-parsing on every access
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import get_storage
from app.models.dataset import Dataset
from app.utils.file_readers import read_structured_file

# ─── Supported File Types ──────────────────────────────────────────
# Maps extensions to logical file type categories
SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".json": "json",
    ".pdf": "pdf",
    ".docx": "word",
    ".doc": "word",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".txt": "text",
}

# Structured types that we can parse into DataFrames
STRUCTURED_TYPES = {"csv", "excel", "json"}

# Maximum file size (in bytes)
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


class DataService:
    """
    Handles file uploads and dataset management.

    Responsibilities:
    - File validation (type, size)
    - Disk storage (organized by user_id)
    - Metadata extraction (columns, types, statistics)
    - CRUD operations on dataset records
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Upload ────────────────────────────────────────────────────

    async def upload_file(self, file: UploadFile, user_id: int) -> Dataset:
        """
        Process and store an uploaded file.

        Steps:
        1. Validate file extension and size
        2. Save to disk under /data/uploads/{user_id}/
        3. Parse metadata for structured files (CSV, Excel, JSON)
        4. Create and return database record

        Raises:
            ValueError: If file type unsupported or file too large
        """
        # Step 1: Validate
        filename = file.filename or "unnamed_file"
        ext = Path(filename).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS.keys()))
            raise ValueError(
                f"Unsupported file type: '{ext}'. Supported: {supported}"
            )

        file_type = SUPPORTED_EXTENSIONS[ext]

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise ValueError("File is empty")

        if file_size > MAX_FILE_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE_MB
            raise ValueError(f"File too large. Maximum size is {max_mb}MB")

        # Step 2: Save via storage backend
        storage = get_storage()
        storage_key = f"{user_id}/{self._unique_filename(filename)}"
        await storage.upload(storage_key, content)

        # For metadata extraction, we need a local path
        local_path = storage.get_local_path(storage_key)

        # Step 3: Extract metadata for structured files
        row_count = None
        column_count = None
        columns_metadata = None

        if file_type in STRUCTURED_TYPES and local_path:
            try:
                row_count, column_count, columns_metadata = self._extract_metadata(
                    local_path, file_type
                )
            except Exception:
                pass

        # Step 4: Create database record
        dataset = Dataset(
            user_id=user_id,
            name=filename,
            file_type=file_type,
            file_path=storage_key,  # Storage key, not absolute path
            file_size_bytes=file_size,
            row_count=row_count,
            column_count=column_count,
            columns_metadata=columns_metadata,
        )
        self.db.add(dataset)
        await self.db.flush()
        await self.db.refresh(dataset)
        return dataset

    # ─── Metadata Extraction ───────────────────────────────────────

    def _extract_metadata(
        self, file_path: Path, file_type: str
    ) -> tuple[int, int, list[dict]]:
        """
        Parse a structured file and extract column metadata.

        Returns:
            (row_count, column_count, columns_metadata)

        columns_metadata is a list of dicts:
        [
            {
                "name": "column_name",
                "dtype": "int64",
                "null_count": 5,
                "null_percent": 2.5,
                "unique_count": 150,
                "sample_values": ["val1", "val2", "val3"]
            },
            ...
        ]

        Why this structure?
        - Frontend can display a table overview immediately
        - ML module uses dtype to determine encoding strategy
        - Null info helps users assess data quality
        - Sample values give a quick data preview without loading full file
        """
        df = self._read_to_dataframe(file_path, file_type)

        row_count = len(df)
        column_count = len(df.columns)

        columns_metadata = []
        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            null_percent = round((null_count / row_count * 100), 2) if row_count > 0 else 0.0

            # Get sample values (up to 5 unique non-null values)
            non_null = series.dropna()
            unique_vals = non_null.unique()
            sample_values = [str(v) for v in unique_vals[:5]]

            columns_metadata.append({
                "name": str(col),
                "dtype": str(series.dtype),
                "null_count": null_count,
                "null_percent": null_percent,
                "unique_count": int(series.nunique()),
                "sample_values": sample_values,
            })

        return row_count, column_count, columns_metadata

    def _read_to_dataframe(self, file_path: Path, file_type: str):
        """Read a structured file into a DataFrame (delegates to shared utility)."""
        return read_structured_file(file_path, file_type)

    # ─── Data Preview ──────────────────────────────────────────────

    def get_preview(self, dataset: Dataset, num_rows: int = 50) -> dict:
        """
        Get a preview of the dataset (first N rows).

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "total_rows": 1000,
                "preview_rows": 50,
                "dtypes": {"col1": "int64", "col2": "object", ...}
            }

        Only works for structured data (CSV, Excel, JSON).
        Returns None for unstructured files.
        """
        if dataset.file_type not in STRUCTURED_TYPES:
            return {
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "preview_rows": 0,
                "dtypes": {},
                "message": f"Preview not available for {dataset.file_type} files",
            }

        file_path = self._resolve_local_path(dataset.file_path)
        if not file_path:
            raise FileNotFoundError(f"Dataset file not found: {dataset.file_path}")

        df = self._read_to_dataframe(file_path, dataset.file_type)

        # Limit to requested rows
        preview_df = df.head(num_rows)

        # Convert to serializable format
        # NaN/NaT → None for clean JSON
        rows = preview_df.where(preview_df.notna(), None).values.tolist()

        # Convert non-serializable types to strings
        clean_rows = []
        for row in rows:
            clean_row = []
            for val in row:
                if val is None:
                    clean_row.append(None)
                elif isinstance(val, int | float | bool | str):
                    clean_row.append(val)
                else:
                    clean_row.append(str(val))
            clean_rows.append(clean_row)

        return {
            "columns": list(df.columns),
            "rows": clean_rows,
            "total_rows": len(df),
            "preview_rows": len(preview_df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    # ─── CRUD Operations ──────────────────────────────────────────

    async def list_datasets(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> tuple[list[Dataset], int]:
        """
        List datasets for a user with pagination.

        Returns:
            (list of datasets, total count)
        """
        # Count total
        count_result = await self.db.execute(
            select(func.count(Dataset.id)).where(Dataset.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Fetch page
        result = await self.db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        datasets = list(result.scalars().all())
        return datasets, total

    async def get_dataset(self, dataset_id: int, user_id: int) -> Optional[Dataset]:
        """Get a single dataset (must be owned by the user)."""
        result = await self.db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_dataset(self, dataset_id: int, user_id: int) -> bool:
        """
        Delete a dataset record and its file from storage.

        Returns True if deleted, False if not found.
        """
        dataset = await self.get_dataset(dataset_id, user_id)
        if not dataset:
            return False

        # Remove file from storage
        storage = get_storage()
        await storage.delete(dataset.file_path)

        await self.db.delete(dataset)
        return True

    # ─── Helpers ───────────────────────────────────────────────────

    def _resolve_local_path(self, storage_key: str) -> Optional[Path]:
        """
        Resolve a storage key to a local filesystem path.
        
        For LocalStorage: returns the direct path.
        For S3Storage: would download to a temp file (future enhancement).
        Also handles legacy absolute paths from before the storage refactor.
        """
        storage = get_storage()

        # First try the storage backend
        local_path = storage.get_local_path(storage_key)
        if local_path:
            return local_path

        # Fallback: legacy absolute paths from before the storage abstraction
        legacy_path = Path(storage_key)
        if legacy_path.is_absolute() and legacy_path.exists():
            return legacy_path

        return None

    @staticmethod
    def _unique_filename(filename: str) -> str:
        """Generate a unique filename using a UUID prefix to avoid collisions."""
        import uuid
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    @staticmethod
    def _get_unique_path(directory: Path, filename: str) -> Path:
        """
        Generate a unique file path to avoid overwriting existing files.

        If 'data.csv' exists, returns 'data_1.csv', 'data_2.csv', etc.
        """
        path = directory / filename
        if not path.exists():
            return path

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            path = directory / new_name
            if not path.exists():
                return path
            counter += 1
