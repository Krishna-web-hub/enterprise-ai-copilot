"""
Phase 10 Tests - Generative AI Report Generation

Coverage:
1. Generate a report (mocked LLM) with and without a dataset
2. Report is persisted and retrievable via list/get
3. Delete a report
4. Error handling: bad report type, nonexistent dataset, nonexistent report, auth

LLM calls are mocked — no OpenAI API key needed.
Database/client/auth fixtures from conftest.py.
"""

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

SAMPLE_CSV = "product,revenue,quantity\nA,10000,50\nB,20000,30\nC,15000,40\n"


async def _upload_csv(client: AsyncClient, auth_headers: dict) -> int:
    files = {"file": ("sales.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_generate_report_without_dataset(client: AsyncClient, auth_headers: dict):
    """Generate a general report (no dataset) with mocked LLM."""
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="# Executive Summary\n\nKey finding: Business is growing steadily."):
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "executive_summary"},
            headers=auth_headers,
        )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["report_type"] == "executive_summary"
    assert "Executive Summary" in data["title"]
    assert len(data["content"]) > 0
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_generate_report_with_dataset(client: AsyncClient, auth_headers: dict):
    """Generate a report grounded in a dataset's KPIs."""
    dataset_id = await _upload_csv(client, auth_headers)

    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="# Sales Analysis\n\nTotal revenue: $45,000 across 3 products."):
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "sales_analysis", "dataset_id": dataset_id},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["report_type"] == "sales_analysis"
    assert "sales.csv" in data["title"]


@pytest.mark.asyncio
async def test_generate_report_with_additional_context(client: AsyncClient, auth_headers: dict):
    """Additional context is passed through to the LLM."""
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="# Recommendations\n\n1. Focus on product B.") as mock_llm:
        response = await client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "recommendation_report",
                "additional_context": "Focus on Q4 results specifically",
            },
            headers=auth_headers,
        )

    assert response.status_code == 201
    # Verify the additional context made it into the LLM call
    call_args = mock_llm.call_args
    assert "Q4" in call_args.kwargs.get("user_prompt", "") or "Q4" in str(call_args)


@pytest.mark.asyncio
async def test_list_reports(client: AsyncClient, auth_headers: dict):
    """List endpoint returns generated reports."""
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="Report content here"):
        await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "executive_summary"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "forecast_report"},
            headers=auth_headers,
        )

    response = await client.get("/api/v1/reports/reports", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["reports"]) == 2


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient, auth_headers: dict):
    """Get a specific report by ID."""
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="Detailed anomaly analysis here"):
        create_resp = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "anomaly_report"},
            headers=auth_headers,
        )
    report_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/reports/reports/{report_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == report_id
    assert response.json()["content"] == "Detailed anomaly analysis here"


@pytest.mark.asyncio
async def test_get_nonexistent_report(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/reports/reports/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_report(client: AsyncClient, auth_headers: dict):
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock,
               return_value="To be deleted"):
        create_resp = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "customer_insights"},
            headers=auth_headers,
        )
    report_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/reports/reports/{report_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/reports/reports/{report_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_nonexistent_dataset(client: AsyncClient, auth_headers: dict):
    """Referencing a nonexistent dataset should fail."""
    with patch("app.services.llm_service.LLMService.complete", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "sales_analysis", "dataset_id": 99999},
            headers=auth_headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/reports/generate",
        json={"report_type": "executive_summary"},
    )
    assert response.status_code == 401
