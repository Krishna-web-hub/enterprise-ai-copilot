"""
SQL Engine Schemas (Pydantic)

Defines request/response shapes for the natural-language-to-SQL endpoint.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SQLQueryRequest(BaseModel):
    """A natural-language question about a specific dataset."""
    dataset_id: int
    question: str = Field(..., min_length=1, max_length=2000)


class SQLQueryResponse(BaseModel):
    """Result of running a natural-language question through the NL2SQL pipeline."""
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    explanation: str
    execution_time_ms: int


class SQLQueryErrorResponse(BaseModel):
    """Returned when NL2SQL generation or execution fails."""
    error: str
    generated_sql: Optional[str] = None


class SQLQueryLogResponse(BaseModel):
    """A single entry from the query history/audit log."""
    id: int
    dataset_id: int
    question: str
    generated_sql: Optional[str] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SQLQueryLogListResponse(BaseModel):
    """Paginated list of past queries for a user."""
    logs: list[SQLQueryLogResponse]
    total: int
