"""
Phase 3 Integration Tests - Data Ingestion

Tests the complete flow:
1. Register a user
2. Login to get a token
3. Upload a CSV file
4. List datasets
5. Get dataset details (verify metadata extraction)
6. Preview dataset rows
7. Delete dataset

Database/client/auth fixtures come from conftest.py (shared across all test files).
"""

import io

import pytest
from httpx import AsyncClient

# ─── Sample data ──────────────────────────────────────────────

SAMPLE_CSV = """name,age,city,salary
Alice,30,New York,75000
Bob,25,San Francisco,82000
Charlie,35,Chicago,90000
Diana,28,Boston,71000
Eve,32,Seattle,88000
"""

SAMPLE_JSON = """[
  {"product": "Widget A", "price": 29.99, "quantity": 100},
  {"product": "Widget B", "price": 49.99, "quantity": 50},
  {"product": "Widget C", "price": 19.99, "quantity": 200}
]"""


# ─── Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_csv(client: AsyncClient, auth_headers: dict):
    """Test uploading a CSV file and verify metadata extraction."""
    files = {"file": ("sales_data.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}

    response = await client.post(
        "/api/v1/data/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "sales_data.csv"
    assert data["file_type"] == "csv"
    assert data["row_count"] == 5
    assert data["column_count"] == 4
    assert data["file_size_bytes"] > 0
    assert data["id"] is not None

    # Verify column metadata was extracted
    columns = data["columns_metadata"]
    assert len(columns) == 4

    # Check the 'name' column
    name_col = next(c for c in columns if c["name"] == "name")
    assert name_col["dtype"] in ("object", "str")  # pandas 2.x may use "str"
    assert name_col["null_count"] == 0
    assert name_col["unique_count"] == 5

    # Check the 'age' column
    age_col = next(c for c in columns if c["name"] == "age")
    assert "int" in age_col["dtype"]


@pytest.mark.asyncio
async def test_upload_json(client: AsyncClient, auth_headers: dict):
    """Test uploading a JSON file."""
    files = {"file": ("products.json", io.BytesIO(SAMPLE_JSON.encode()), "application/json")}

    response = await client.post(
        "/api/v1/data/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "products.json"
    assert data["file_type"] == "json"
    assert data["row_count"] == 3
    assert data["column_count"] == 3


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient, auth_headers: dict):
    """Test that unsupported file types are rejected."""
    files = {"file": ("virus.exe", io.BytesIO(b"malicious"), "application/octet-stream")}

    response = await client.post(
        "/api/v1/data/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, auth_headers: dict):
    """Test that empty files are rejected."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}

    response = await client.post(
        "/api/v1/data/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_datasets(client: AsyncClient, auth_headers: dict):
    """Test listing datasets with pagination."""
    # Upload two files
    for name in ["data1.csv", "data2.csv"]:
        files = {"file": (name, io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
        await client.post("/api/v1/data/upload", files=files, headers=auth_headers)

    # List
    response = await client.get("/api/v1/data/datasets", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["datasets"]) == 2
    assert data["skip"] == 0
    assert data["limit"] == 20


@pytest.mark.asyncio
async def test_get_dataset_detail(client: AsyncClient, auth_headers: dict):
    """Test getting a single dataset by ID."""
    # Upload
    files = {"file": ("detail_test.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    upload_resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    dataset_id = upload_resp.json()["id"]

    # Get detail
    response = await client.get(f"/api/v1/data/datasets/{dataset_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == dataset_id
    assert data["name"] == "detail_test.csv"
    assert data["columns_metadata"] is not None


@pytest.mark.asyncio
async def test_get_nonexistent_dataset(client: AsyncClient, auth_headers: dict):
    """Test 404 for non-existent dataset."""
    response = await client.get("/api/v1/data/datasets/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_dataset(client: AsyncClient, auth_headers: dict):
    """Test data preview returns correct rows."""
    # Upload
    files = {"file": ("preview_test.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    upload_resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    dataset_id = upload_resp.json()["id"]

    # Preview
    response = await client.get(
        f"/api/v1/data/datasets/{dataset_id}/preview?rows=3",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["name", "age", "city", "salary"]
    assert data["preview_rows"] == 3
    assert data["total_rows"] == 5
    assert len(data["rows"]) == 3
    # First row should be Alice
    assert data["rows"][0][0] == "Alice"


@pytest.mark.asyncio
async def test_delete_dataset(client: AsyncClient, auth_headers: dict):
    """Test deleting a dataset removes it from the list."""
    # Upload
    files = {"file": ("to_delete.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    upload_resp = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    dataset_id = upload_resp.json()["id"]

    # Delete
    response = await client.delete(f"/api/v1/data/datasets/{dataset_id}", headers=auth_headers)
    assert response.status_code == 200

    # Verify gone
    response = await client.get(f"/api/v1/data/datasets/{dataset_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    """Test that upload fails without authentication."""
    files = {"file": ("noauth.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}

    response = await client.post("/api/v1/data/upload", files=files)
    assert response.status_code == 401
