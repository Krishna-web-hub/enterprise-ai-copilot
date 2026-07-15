"""
Phase 9 Tests - Dashboard, KPIs & Power BI Export

Coverage:
1. Dashboard endpoint: returns correct counts after uploading data/creating sessions
2. KPI computation: produces expected summary KPIs, numeric stats, category breakdowns
3. Power BI export: CSV returns valid content, Excel returns valid file
4. Error handling: nonexistent dataset, non-structured dataset
5. Auth required

Database/client/auth fixtures from conftest.py.
"""

import io

import pytest
from httpx import AsyncClient

SAMPLE_SALES_CSV = """product,revenue,quantity,category,date
Widget A,29000,100,Electronics,2024-01-15
Widget B,49000,50,Electronics,2024-02-10
Widget C,19000,200,Home,2024-03-05
Widget D,35000,75,Clothing,2024-04-20
Widget E,62000,30,Electronics,2024-05-12
"""


async def _upload_sales_csv(client: AsyncClient, auth_headers: dict) -> int:
    files = {"file": ("sales.csv", io.BytesIO(SAMPLE_SALES_CSV.encode()), "text/csv")}
    response = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


# ─── Dashboard Tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_empty(client: AsyncClient, auth_headers: dict):
    """Dashboard returns zeros when user has no data."""
    response = await client.get("/api/v1/reports/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_datasets"] == 0
    assert data["total_models"] == 0
    assert data["total_documents"] == 0
    assert data["total_chat_sessions"] == 0
    assert data["recent_chats"] == []
    assert data["recent_datasets"] == []


@pytest.mark.asyncio
async def test_dashboard_with_data(client: AsyncClient, auth_headers: dict):
    """Dashboard reflects uploaded datasets and created chat sessions."""
    # Upload a dataset
    await _upload_sales_csv(client, auth_headers)

    # Create a chat session
    await client.post("/api/v1/chat/sessions", json={"title": "Test Chat"}, headers=auth_headers)

    response = await client.get("/api/v1/reports/dashboard", headers=auth_headers)
    data = response.json()
    assert data["total_datasets"] == 1
    assert data["total_chat_sessions"] == 1
    assert len(data["recent_datasets"]) == 1
    assert data["recent_datasets"][0]["name"] == "sales.csv"
    assert len(data["recent_chats"]) == 1


# ─── KPI Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_kpis(client: AsyncClient, auth_headers: dict):
    """KPI endpoint returns meaningful stats for a sales dataset."""
    dataset_id = await _upload_sales_csv(client, auth_headers)

    response = await client.post(
        "/api/v1/reports/kpis",
        json={"dataset_id": dataset_id},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dataset_name"] == "sales.csv"
    assert data["row_count"] == 5
    assert data["column_count"] == 5

    # Should have summary KPIs (revenue and quantity are business-named columns)
    kpi_names = [k["name"].lower() for k in data["summary_kpis"]]
    assert any("revenue" in n for n in kpi_names) or any("quantity" in n for n in kpi_names)

    # Numeric stats should include revenue and quantity
    stat_cols = [s["column"] for s in data["numeric_stats"]]
    assert "revenue" in stat_cols
    assert "quantity" in stat_cols

    # Revenue total should be 29000+49000+19000+35000+62000 = 194000
    revenue_stat = next(s for s in data["numeric_stats"] if s["column"] == "revenue")
    assert revenue_stat["sum"] == 194000.0

    # Category breakdown for 'category' column (3 unique values <= 10 threshold)
    assert len(data["category_breakdowns"]) > 0
    cat_breakdown = next((b for b in data["category_breakdowns"] if b["column"] == "category"), None)
    assert cat_breakdown is not None
    assert len(cat_breakdown["top_values"]) == 3  # Electronics, Home, Clothing


@pytest.mark.asyncio
async def test_kpis_detects_time_trends(client: AsyncClient, auth_headers: dict):
    """KPI endpoint detects date column and computes monthly trends."""
    dataset_id = await _upload_sales_csv(client, auth_headers)

    response = await client.post(
        "/api/v1/reports/kpis",
        json={"dataset_id": dataset_id},
        headers=auth_headers,
    )

    data = response.json()
    # 'date' column should be detected as a date column
    assert len(data["time_trends"]) > 0
    # Each trend entry should have a period and metrics
    assert "period" in data["time_trends"][0]
    assert "metrics" in data["time_trends"][0]


@pytest.mark.asyncio
async def test_kpis_nonexistent_dataset(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/reports/kpis",
        json={"dataset_id": 99999},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ─── Power BI Export Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_export_csv(client: AsyncClient, auth_headers: dict):
    """CSV export returns valid CSV content."""
    dataset_id = await _upload_sales_csv(client, auth_headers)

    response = await client.post(
        "/api/v1/reports/powerbi/export",
        json={"dataset_id": dataset_id, "format": "csv"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers.get("content-disposition", "")

    content = response.text
    lines = content.strip().split("\n")
    assert len(lines) == 6  # header + 5 data rows
    assert "product" in lines[0]
    assert "revenue" in lines[0]


@pytest.mark.asyncio
async def test_export_excel(client: AsyncClient, auth_headers: dict):
    """Excel export returns a valid xlsx file (check magic bytes)."""
    dataset_id = await _upload_sales_csv(client, auth_headers)

    response = await client.post(
        "/api/v1/reports/powerbi/export",
        json={"dataset_id": dataset_id, "format": "excel"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    # xlsx files start with PK (zip format)
    assert response.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_nonexistent_dataset(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/reports/powerbi/export",
        json={"dataset_id": 99999, "format": "csv"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ─── Auth ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/reports/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_kpis_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/reports/kpis", json={"dataset_id": 1})
    assert response.status_code == 401
