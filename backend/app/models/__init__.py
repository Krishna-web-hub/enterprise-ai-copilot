"""
ORM Models Package

All models MUST be imported here so SQLAlchemy's metadata object
knows about them when creating tables or generating migrations.

Without these imports, Base.metadata.create_all() would create an empty database,
and Alembic would generate empty migrations — a common gotcha.
"""

from app.models.chat import ChatMessage, ChatSession
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.ml_model import MLModel
from app.models.report import Report
from app.models.sql_query_log import SQLQueryLog
from app.models.user import User

__all__ = [
    "User",
    "Dataset",
    "Document",
    "ChatSession",
    "ChatMessage",
    "MLModel",
    "Report",
    "SQLQueryLog",
]
