"""
Celery Application Configuration

Creates and configures the Celery app instance used for background task execution.

Why Celery?
- Non-blocking: Heavy operations (ML training, RAG ingestion, report generation)
  run in a separate worker process, freeing the API server to handle more requests.
- Scalable: Add more workers to handle more concurrent background jobs.
- Reliable: Tasks are persisted in Redis. If a worker crashes, the task retries.
- Observable: Built-in task state tracking (PENDING, STARTED, SUCCESS, FAILURE).

Architecture:
- Broker: Redis (messages are queued here)
- Backend: Redis (task results are stored here for status polling)
- Worker: Separate process started with `celery -A app.core.celery_app worker`

Usage:
    from app.core.celery_app import celery_app

    @celery_app.task(bind=True)
    def my_task(self, arg1, arg2):
        ...
"""

from celery import Celery

from app.core.config import settings

# Create the Celery app
celery_app = Celery(
    "enterprise_ai_copilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_track_started=True,       # Report STARTED state (not just PENDING/SUCCESS/FAILURE)
    task_time_limit=600,           # Hard kill after 10 minutes
    task_soft_time_limit=300,      # Soft limit (raises SoftTimeLimitExceeded) at 5 min
    task_acks_late=True,           # Acknowledge after execution (enables retry on worker crash)
    worker_prefetch_multiplier=1,  # Fetch one task at a time (fair scheduling)

    # Result expiration (clean up completed task results after 1 hour)
    result_expires=3600,

    # Task discovery — auto-discover tasks in these modules
    include=[
        "app.tasks.ml_tasks",
        "app.tasks.rag_tasks",
        "app.tasks.report_tasks",
    ],
)
