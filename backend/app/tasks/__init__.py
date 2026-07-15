"""
Background Tasks Package

Celery task definitions for long-running operations:
- ML model training
- RAG document ingestion
- Report generation

These tasks are discovered automatically by the Celery app
(configured in app/core/celery_app.py).
"""
