"""
Chat Schemas (Pydantic)

Defines request/response shapes for chat sessions and messages.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    title: str = Field(default="New Chat", max_length=255)


class ChatSessionResponse(BaseModel):
    """Chat session details."""
    id: int
    title: str
    is_pinned: bool = False
    pin_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""
    sessions: list[ChatSessionResponse]
    total: int


class ChatSessionUpdate(BaseModel):
    """Update a chat session (rename)."""
    title: str = Field(..., min_length=1, max_length=255)


class ChatMessageRequest(BaseModel):
    """User message sent to the AI."""
    content: str = Field(..., min_length=1, max_length=10000)
    dataset_id: Optional[int] = None  # Optional context: which dataset to query


class ChatMessageResponse(BaseModel):
    """AI response to a user message."""
    id: int
    role: str
    content: str
    metadata: Optional[dict] = None  # SQL query, sources, agent used, etc.
    created_at: datetime

    model_config = {"from_attributes": True}
