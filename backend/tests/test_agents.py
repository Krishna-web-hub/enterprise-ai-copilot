"""
Phase 8 Tests - Agentic AI (Chat + Orchestrator)

Coverage:
1. Chat session CRUD: create, list, get messages
2. Full agentic message flow: send message → planner (mocked) → general agent
   (mocked) → response saved with metadata
3. Planner routes to correct agent based on mock plan
4. Error handling: nonexistent session, auth required
5. Orchestrator logic: synthesizer combines multi-step results, handles failures

All LLM calls are mocked — no OpenAI API key needed for tests.
Database/client/auth fixtures from conftest.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ─── Chat Session CRUD ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Sales Analysis"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Sales Analysis"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, auth_headers: dict):
    # Create two sessions
    await client.post("/api/v1/chat/sessions", json={"title": "Session 1"}, headers=auth_headers)
    await client.post("/api/v1/chat/sessions", json={"title": "Session 2"}, headers=auth_headers)

    response = await client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["sessions"]) == 2


@pytest.mark.asyncio
async def test_get_messages_empty_session(client: AsyncClient, auth_headers: dict):
    # Create a session
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "Empty"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["messages"] == []


@pytest.mark.asyncio
async def test_send_message_nonexistent_session(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/sessions/99999/messages",
        json={"content": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "test"},
    )
    assert response.status_code == 401


# ─── Agentic Message Flow (mocked LLM) ──────────────────────────

@pytest.mark.asyncio
async def test_send_message_general_agent(client: AsyncClient, auth_headers: dict):
    """
    Full flow: send message → planner routes to general agent → response with metadata.
    Mock the planner to return a general agent plan, mock the general agent's LLM call.
    """
    # Create session
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "Test Chat"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    # Mock the planner to return a simple general-agent plan
    mock_planner_result = {
        "plan": [{"agent": "general", "instruction": "What is machine learning?"}],
        "plan_reasoning": "General knowledge question, no data tools needed",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "General knowledge question", "plan_steps": [{"agent": "general", "instruction": "What is machine learning?"}]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result), \
         patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock, return_value="Machine learning is a field of AI that enables systems to learn from data."):

        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "What is machine learning?"},
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["role"] == "assistant"
    assert "machine learning" in data["content"].lower() or "Machine learning" in data["content"]
    assert data["metadata"] is not None
    assert "agents_used" in data["metadata"]
    assert "general" in data["metadata"]["agents_used"]


@pytest.mark.asyncio
async def test_send_message_saves_both_messages(client: AsyncClient, auth_headers: dict):
    """After sending a message, both user + assistant messages appear in history."""
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "History Test"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    mock_planner_result = {
        "plan": [{"agent": "general", "instruction": "Hello"}],
        "plan_reasoning": "Simple greeting",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "Simple greeting", "plan_steps": [{"agent": "general", "instruction": "Hello"}]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result), \
         patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock, return_value="Hello! How can I help you?"):

        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Hello"},
            headers=auth_headers,
        )

    # Check history
    history_resp = await client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=auth_headers)
    messages = history_resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert "Hello" in messages[1]["content"]


@pytest.mark.asyncio
async def test_planner_routes_to_sql_agent(client: AsyncClient, auth_headers: dict):
    """When planner selects sql_agent, verify it's reflected in metadata."""
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "SQL Test"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    mock_planner_result = {
        "plan": [{"agent": "sql_agent", "instruction": "Show total sales"}],
        "plan_reasoning": "Data question requiring SQL query",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "Data question", "plan_steps": [{"agent": "sql_agent", "instruction": "Show total sales"}]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result):
        # sql_agent will fail (no datasets) but the routing is what matters
        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Show total sales"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "sql_agent" in data["metadata"]["agents_used"]


@pytest.mark.asyncio
async def test_planner_routes_to_rag_agent(client: AsyncClient, auth_headers: dict):
    """When planner selects rag_agent, verify it's reflected in metadata."""
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "RAG Test"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    mock_planner_result = {
        "plan": [{"agent": "rag_agent", "instruction": "What is the leave policy?"}],
        "plan_reasoning": "Document question requiring RAG",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "Document question", "plan_steps": [{"agent": "rag_agent", "instruction": "What is the leave policy?"}]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result):
        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "What is the leave policy?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "rag_agent" in data["metadata"]["agents_used"]


@pytest.mark.asyncio
async def test_multi_step_plan(client: AsyncClient, auth_headers: dict):
    """Multi-step plan: planner produces 2 steps, both execute sequentially."""
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "Multi Step"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    mock_planner_result = {
        "plan": [
            {"agent": "sql_agent", "instruction": "Get sales data"},
            {"agent": "general", "instruction": "Summarize the findings"},
        ],
        "plan_reasoning": "Need data first, then summarize",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "Need data first, then summarize", "plan_steps": [
            {"agent": "sql_agent", "instruction": "Get sales data"},
            {"agent": "general", "instruction": "Summarize the findings"},
        ]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result), \
         patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock, return_value="Based on the available data, here is a summary."):

        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Summarize my sales data"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    # Both agents should appear in metadata
    assert len(data["metadata"]["agents_used"]) == 2
    assert "sql_agent" in data["metadata"]["agents_used"]
    assert "general" in data["metadata"]["agents_used"]


@pytest.mark.asyncio
async def test_metadata_includes_timing(client: AsyncClient, auth_headers: dict):
    """Response metadata should include total_time_ms."""
    create_resp = await client.post(
        "/api/v1/chat/sessions", json={"title": "Timing"}, headers=auth_headers
    )
    session_id = create_resp.json()["id"]

    mock_planner_result = {
        "plan": [{"agent": "general", "instruction": "Hi"}],
        "plan_reasoning": "Simple",
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": "Simple", "plan_steps": [{"agent": "general", "instruction": "Hi"}]},
    }

    with patch("app.agents.orchestrator.planner_node", new_callable=AsyncMock, return_value=mock_planner_result), \
         patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock, return_value="Hi there!"):

        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Hi"},
            headers=auth_headers,
        )

    data = response.json()
    assert "total_time_ms" in data["metadata"]
    assert isinstance(data["metadata"]["total_time_ms"], int)
    assert data["metadata"]["total_time_ms"] >= 0
