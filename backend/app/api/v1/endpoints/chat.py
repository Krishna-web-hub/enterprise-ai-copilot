"""
Chat & AI Endpoints

The primary conversational interface. Users send messages and the system
routes them through the agentic AI pipeline (Planner → specialized agents
→ synthesized answer).

This is where all the capabilities built in Phases 4-7 (SQL, ML, Vision,
RAG) come together under one intelligent routing layer.

Routes:
- POST /sessions                   → Create a new chat session
- GET  /sessions                   → List user's chat sessions
- POST /sessions/{id}/messages     → Send a message, get AI response
- GET  /sessions/{id}/messages     → Get chat history for a session
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.storage import get_storage
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new chat session.

    A session groups related messages into a conversation thread.
    Users can have multiple sessions (like different chat topics).
    """
    chat_service = ChatService(db)
    session = await chat_service.create_session(current_user.id, request.title)
    return session


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions for the current user, newest first."""
    chat_service = ChatService(db)
    sessions = await chat_service.list_sessions(current_user.id)
    return ChatSessionListResponse(sessions=sessions, total=len(sessions))


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: int,
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the AI and receive a response.

    The system automatically determines the best approach by running
    the Planner Agent, which may invoke:
    - SQL Agent for data questions
    - RAG Agent for document questions
    - ML Agent for prediction/model questions
    - Vision Agent for image analysis questions
    - General Agent for explanations and summarization

    The response includes metadata showing which agents were used,
    their execution results, and timing information.
    """
    chat_service = ChatService(db)

    # Verify the session exists and belongs to the user
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )

    # Process through the agentic pipeline
    ai_message = await chat_service.process_user_message(
        session_id=session_id,
        content=request.content,
        user_id=current_user.id,
    )

    return ChatMessageResponse(
        id=ai_message.id,
        role=ai_message.role,
        content=ai_message.content,
        metadata=ai_message.metadata_,
        created_at=ai_message.created_at,
    )


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a chat session (conversation history)."""
    chat_service = ChatService(db)

    # Verify the session exists and belongs to the user
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )

    messages = await chat_service.get_messages(session_id)

    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata_,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": len(messages),
    }


@router.post("/sessions/{session_id}/messages/multimodal", response_model=ChatMessageResponse)
async def send_multimodal_message(
    session_id: int,
    content: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message with file attachments (images, PDFs, audio) for AI analysis.

    The system will:
    - Store uploaded files
    - Describe/analyze images via Vision Agent
    - Transcribe audio (if applicable)
    - Process PDFs/documents via RAG
    - Route the combined context through the agentic pipeline
    """
    chat_service = ChatService(db)

    # Verify session ownership
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )

    # Process attachments
    attachment_metadata: list[dict] = []
    storage = get_storage()

    for file in files:
        if not file.filename:
            continue

        file_bytes = await file.read()
        file_size = len(file_bytes)

        # Determine file type category
        content_type = file.content_type or ""
        if content_type.startswith("image/"):
            file_category = "image"
        elif content_type.startswith("audio/"):
            file_category = "audio"
        elif content_type in ("application/pdf",):
            file_category = "pdf"
        else:
            file_category = "document"

        # Store the file
        storage_key = f"chat_attachments/{current_user.id}/{session_id}/{file.filename}"
        await storage.upload(storage_key, file_bytes)

        attachment_metadata.append({
            "filename": file.filename,
            "content_type": content_type,
            "category": file_category,
            "size_bytes": file_size,
            "storage_key": storage_key,
        })

    # Build the enriched message content
    message_text = content.strip() if content else ""

    # Add attachment descriptions to the message for the AI
    if attachment_metadata:
        attachment_descriptions = []
        for att in attachment_metadata:
            attachment_descriptions.append(
                f"[Attached {att['category']}: {att['filename']} ({att['size_bytes']} bytes)]"
            )
        if message_text:
            enriched_content = message_text + "\n\n" + "\n".join(attachment_descriptions)
        else:
            enriched_content = "Please analyze the attached files:\n" + "\n".join(attachment_descriptions)
    else:
        enriched_content = message_text

    if not enriched_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must contain text or at least one file attachment",
        )

    # Process through the agentic pipeline with attachment metadata
    ai_message = await chat_service.process_user_message(
        session_id=session_id,
        content=enriched_content,
        user_id=current_user.id,
    )

    # Include attachment info in the response metadata
    if attachment_metadata and ai_message.metadata_:
        ai_message.metadata_["attachments"] = attachment_metadata
    elif attachment_metadata:
        ai_message.metadata_ = {"attachments": attachment_metadata}

    return ChatMessageResponse(
        id=ai_message.id,
        role=ai_message.role,
        content=ai_message.content,
        metadata=ai_message.metadata_,
        created_at=ai_message.created_at,
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def rename_session(
    session_id: int,
    request: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a chat session."""
    chat_service = ChatService(db)
    session = await chat_service.rename_session(session_id, current_user.id, request.title)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    chat_service = ChatService(db)
    deleted = await chat_service.delete_session(session_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )


@router.post("/sessions/{session_id}/pin", response_model=ChatSessionResponse)
async def pin_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pin a chat session (max 5 pinned)."""
    chat_service = ChatService(db)
    session = await chat_service.pin_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or max 5 pinned sessions reached",
        )
    return session


@router.delete("/sessions/{session_id}/pin", response_model=ChatSessionResponse)
async def unpin_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpin a chat session."""
    chat_service = ChatService(db)
    session = await chat_service.unpin_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    return session
