"""
Shared File Reading Utilities

Centralizes "read a structured file into a pandas DataFrame" logic so it's
not duplicated between DataService (metadata extraction, preview) and
SQLEngineService (NL2SQL execution).

Why pandas as the intermediate format?
- Consistent type inference across CSV/Excel/JSON regardless of downstream use
- DuckDB can register a pandas DataFrame as a queryable view directly
  (conn.register), so we don't need per-format SQL readers
"""

import json
from pathlib import Path

import pandas as pd

# Row cap when reading files for metadata/preview/query purposes.
# Prevents loading an enormous file entirely into memory for a preview or query.
DEFAULT_READ_LIMIT = 10000


def read_structured_file(file_path: Path, file_type: str, nrows: int = DEFAULT_READ_LIMIT) -> pd.DataFrame:
    """
    Read a structured file (CSV, Excel, or JSON) into a pandas DataFrame.

    Args:
        file_path: Path to the file on disk
        file_type: One of "csv", "excel", "json"
        nrows: Maximum rows to read (protects against huge files)

    Returns:
        A pandas DataFrame with the file's contents

    Raises:
        ValueError: If file_type is not a supported structured type or parsing fails
    """
    if file_type == "csv":
        # Try utf-8 first, fall back to latin-1 (handles most encodings)
        try:
            return pd.read_csv(file_path, nrows=nrows)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="latin-1", nrows=nrows)

    elif file_type == "excel":
        return pd.read_excel(file_path, nrows=nrows)

    elif file_type == "json":
        # Try reading as records first, then as generic JSON
        try:
            return pd.read_json(file_path, nrows=nrows)
        except ValueError:
            # Might be a nested JSON — try normalize
            with open(file_path) as f:
                data = json.load(f)
            if isinstance(data, list):
                return pd.json_normalize(data)
            elif isinstance(data, dict):
                # Wrap single object in a list
                return pd.json_normalize([data])
            else:
                raise ValueError("JSON must be an object or array of objects")

    raise ValueError(f"Cannot parse file type: {file_type}")
