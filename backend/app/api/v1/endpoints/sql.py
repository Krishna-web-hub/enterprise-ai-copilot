"""
SQL Engine Endpoints — Natural Language to SQL

Lets users ask business questions in plain English about a specific
dataset. The system generates SQL, executes it safely against the
dataset's file (via DuckDB), and returns both the raw results and a
natural-language explanation.

This is a standalone endpoint (not yet wired into /chat). Once the
Agentic AI module (Phase 8) exists, the Planner Agent's SQL Agent will
call NL2SQLService directly rather than going through this HTTP layer —
this endpoint remains useful on its own for a dedicated "Ask your data"
UI and for direct API consumers.

Routes:
- POST /query           → Ask a natural-language question about a dataset
- GET  /history         → List past queries (audit trail / recent activity)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.sql_query_log import SQLQueryLog
from app.models.user import User
from app.schemas.sql import (
    SQLQueryLogListResponse,
    SQLQueryRequest,
    SQLQueryResponse,
)
from app.services.data_service import DataService
from app.services.llm_service import LLMServiceError
from app.services.nl2sql_service import NL2SQLService
from app.services.sql_engine_service import SQLValidationError

router = APIRouter()


@router.post("/query", response_model=SQLQueryResponse)
async def ask_question(
    request: SQLQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a natural-language business question about a dataset.

    Example: "What were the top 5 products by revenue last month?"

    Pipeline:
    1. Look up the dataset (must be owned by the current user, and must
       be a structured type: CSV, Excel, or JSON)
    2. Generate SQL from the question using the dataset's schema
    3. Validate the SQL is a safe, read-only SELECT
    4. Execute it against the dataset's data (via DuckDB)
    5. Generate a natural-language explanation of the results

    Every attempt (success or failure) is logged for audit purposes.
    """
    data_service = DataService(db)
    dataset = await data_service.get_dataset(request.dataset_id, current_user.id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {request.dataset_id} not found",
        )

    nl2sql = NL2SQLService(db)

    try:
        result = await nl2sql.ask(dataset, request.question, current_user.id)
    except SQLValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not run this query safely: {str(e)}",
        )
    except LLMServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )

    return SQLQueryResponse(**result)


@router.get("/history", response_model=SQLQueryLogListResponse)
async def get_query_history(
    dataset_id: int | None = Query(None, description="Filter by dataset"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List past natural-language queries made by the current user.

    Optionally filter by dataset_id. Useful for a "recent queries"
    dashboard widget and for debugging why a particular query failed.
    """
    conditions = [SQLQueryLog.user_id == current_user.id]
    if dataset_id is not None:
        conditions.append(SQLQueryLog.dataset_id == dataset_id)

    count_result = await db.execute(
        select(func.count(SQLQueryLog.id)).where(*conditions)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(SQLQueryLog)
        .where(*conditions)
        .order_by(SQLQueryLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = list(result.scalars().all())

    return SQLQueryLogListResponse(logs=logs, total=total)
