"""
Chat Service

Manages chat sessions and message processing.
Orchestrates AI responses by routing to the Agent Orchestrator (Phase 8).

The ChatService is the bridge between the HTTP layer (chat endpoints) and
the agentic AI layer (orchestrator). It handles persistence (saving messages
to the database) while the orchestrator handles intelligence (deciding what
agents to invoke and producing the answer).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.models.chat import ChatMessage, ChatSession


class ChatService:
    """Handles chat session management and agentic message processing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: int, title: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: int, user_id: int) -> Optional[ChatSession]:
        """Get a session owned by the user."""
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, user_id: int) -> list[ChatSession]:
        """List all chat sessions for a user, newest first."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(
        self, session_id: int, role: str, content: str, metadata: Optional[dict] = None
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_=metadata,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_messages(self, session_id: int) -> list[ChatMessage]:
        """Get all messages in a session, ordered chronologically."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def rename_session(self, session_id: int, user_id: int, title: str) -> ChatSession | None:
        """Rename a chat session. Returns None if not found."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None
        session.title = title
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: int, user_id: int) -> bool:
        """Delete a chat session and all its messages. Returns False if not found."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return False
        # Delete all messages first
        await self.db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        from sqlalchemy import delete as sa_delete
        await self.db.execute(
            sa_delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        await self.db.delete(session)
        await self.db.flush()
        return True

    async def pin_session(self, session_id: int, user_id: int) -> ChatSession | None:
        """
        Pin a chat session. Max 5 pinned sessions per user.
        Assigns the next pin_order value. Returns None if not found or limit reached.
        """
        session = await self.get_session(session_id, user_id)
        if not session:
            return None

        # Check current pinned count
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.is_pinned == True,
            )
        )
        pinned_sessions = list(result.scalars().all())

        if len(pinned_sessions) >= 5 and not session.is_pinned:
            return None  # Limit reached

        if not session.is_pinned:
            # Assign next pin_order
            max_order = max((s.pin_order for s in pinned_sessions), default=0)
            session.is_pinned = True
            session.pin_order = max_order + 1
            await self.db.flush()
            await self.db.refresh(session)

        return session

    async def unpin_session(self, session_id: int, user_id: int) -> ChatSession | None:
        """Unpin a chat session. Returns None if not found."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None
        session.is_pinned = False
        session.pin_order = 0
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def reorder_pinned(self, session_id: int, user_id: int, new_order: int) -> ChatSession | None:
        """Change the pin_order of a pinned session."""
        session = await self.get_session(session_id, user_id)
        if not session or not session.is_pinned:
            return None
        session.pin_order = new_order
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def process_user_message(self, session_id: int, content: str, user_id: int) -> ChatMessage:
        """
        Process a user message through the agentic AI pipeline.

        Flow:
        1. Save the user's message to the session
        2. Run the Agent Orchestrator (Planner → Agents → Synthesize)
        3. Save the AI's response (with agent metadata) to the session
        4. Return the AI response message

        The orchestrator decides which agents to invoke based on the question
        and what resources (datasets, documents, models) the user has.
        """
        # Save user message
        await self.add_message(session_id, "user", content)

        # Run the agentic pipeline
        orchestrator = AgentOrchestrator(self.db)
        result = await orchestrator.run(
            question=content,
            user_id=user_id,
            session_id=session_id,
        )

        # Save and return the AI response with metadata
        ai_message = await self.add_message(
            session_id=session_id,
            role="assistant",
            content=result["answer"],
            metadata=result["metadata"],
        )

        return ai_message
