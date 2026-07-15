"""
API v1 Router - Aggregates all endpoint routers under /api/v1

Why versioned API?
- Allows breaking changes in v2 without affecting existing clients
- Multiple versions can run simultaneously during migration periods
- Industry standard for public-facing APIs
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, data, ml, rag, reports, sql, tasks, vision

api_router = APIRouter()

# Each router handles a specific domain
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(data.router, prefix="/data", tags=["Data Management"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat & AI"])
api_router.include_router(sql.router, prefix="/sql", tags=["SQL Engine (NL2SQL)"])
api_router.include_router(ml.router, prefix="/ml", tags=["Machine Learning"])
api_router.include_router(vision.router, prefix="/vision", tags=["Vision & Deep Learning"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG (Document Q&A)"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Dashboards"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Background Tasks"])
