"""
Task Status Endpoint

Provides a generic polling endpoint for checking the status of any
background task dispatched via Celery (ML training, RAG ingestion, reports).

Flow:
1. Client POSTs to /ml/train?async=true → gets 202 Accepted + task_id
2. Client polls GET /tasks/{task_id} until status is SUCCESS or FAILURE
3. Once SUCCESS, the result contains the created resource info (model_id, etc.)

Why a single generic endpoint instead of per-domain status endpoints?
- DRY: task status checking logic is identical regardless of task type
- Frontend simplicity: one polling function works for all background operations
- Celery's result backend already stores status per task_id — we just expose it

Routes:
- GET /tasks/{task_id} → Get task status and result
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.celery_app import celery_app
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Check the status of a background task.

    States:
    - PENDING: Task is queued but hasn't started yet
    - STARTED: Task is currently running
    - SUCCESS: Task completed — result available in the response
    - FAILURE: Task failed — error message in the response
    """
    try:
        result = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.status,
        }

        if result.ready():
            if result.successful():
                response["result"] = result.result
            else:
                response["error"] = str(result.result) if result.result else "Task failed"
        elif result.status == "STARTED":
            response["message"] = "Task is currently running..."
        else:
            response["message"] = "Task is queued and waiting for a worker..."

        return response
    except Exception:
        # Redis/Celery backend unavailable
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "message": "Task backend (Redis) is not available. Tasks require Redis to be running.",
        }
