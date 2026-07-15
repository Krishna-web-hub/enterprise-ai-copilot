"""
Phase 4 Tests - SQL Engine (NL2SQL)

Three layers of coverage:
1. Unit tests for SQLEngineService.validate_sql() — the security boundary
   that decides whether LLM-generated SQL is safe to run
2. Unit tests for SQLEngineService.execute_query() — real DuckDB execution
   against a temporary CSV file (no LLM involved)
3. Integration tests for POST /api/v1/sql/query — the full HTTP flow, with
   the LLM calls mocked out (we don't want tests to depend on a real
   OpenAI API key or network access)

Database/client/auth fixtures come from conftest.py.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.dataset import Dataset
from app.services.sql_engine_service import SQLEngineService, SQLValidationError

# ─── SQL Validation Unit Tests ─────────────────────────────────

class TestValidateSql:
    """Tests for the security-critical SQL validator."""

    def test_accepts_simple_select(self):
        result = SQLEngineService.validate_sql("SELECT * FROM dataset")
        assert result == "SELECT * FROM dataset"

    def test_accepts_select_with_trailing_semicolon(self):
        result = SQLEngineService.validate_sql("SELECT * FROM dataset;")
        assert result == "SELECT * FROM dataset"

    def test_accepts_cte_with_select(self):
        sql = 'WITH totals AS (SELECT * FROM dataset) SELECT * FROM totals'
        result = SQLEngineService.validate_sql(sql)
        assert result == sql

    def test_accepts_lowercase_select(self):
        result = SQLEngineService.validate_sql("select * from dataset")
        assert result == "select * from dataset"

    def test_rejects_empty_sql(self):
        with pytest.raises(SQLValidationError, match="empty"):
            SQLEngineService.validate_sql("")

    def test_rejects_whitespace_only_sql(self):
        with pytest.raises(SQLValidationError, match="empty"):
            SQLEngineService.validate_sql("   ")

    def test_rejects_stacked_statements(self):
        with pytest.raises(SQLValidationError, match="Multiple SQL statements"):
            SQLEngineService.validate_sql("SELECT * FROM dataset; DROP TABLE dataset")

    def test_rejects_drop(self):
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.validate_sql("DROP TABLE dataset")

    def test_rejects_delete(self):
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.validate_sql("DELETE FROM dataset")

    def test_rejects_insert(self):
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.validate_sql("INSERT INTO dataset VALUES (1)")

    def test_rejects_update(self):
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.validate_sql("UPDATE dataset SET x = 1")

    def test_rejects_forbidden_keyword_embedded_in_select(self):
        """A forbidden keyword appearing inside an otherwise SELECT-shaped statement is still rejected."""
        with pytest.raises(SQLValidationError, match="disallowed keyword"):
            SQLEngineService.validate_sql(
                "SELECT * FROM dataset WHERE product IN (SELECT product FROM dataset) OR 1=1 CALL foo()"
            )

    def test_rejects_attach_database(self):
        """
        DuckDB-specific attack: ATTACH could open arbitrary files as databases.
        This is caught by the "must start with SELECT/WITH" check, which is
        equally effective — ATTACH can never be disguised as the start of a
        SELECT statement.
        """
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.validate_sql("ATTACH '/etc/passwd' AS pwned")

    def test_does_not_false_positive_on_column_named_like_keyword(self):
        """
        A column literally named 'updated_at' contains the substring 'UPDATE'
        but must NOT trigger the forbidden-keyword check (word-boundary matching).
        """
        result = SQLEngineService.validate_sql('SELECT "updated_at" FROM dataset')
        assert result == 'SELECT "updated_at" FROM dataset'


# ─── DuckDB Execution Unit Tests ───────────────────────────────

@pytest.fixture
def sample_dataset(tmp_path: Path) -> Dataset:
    """A Dataset pointing at a real temporary CSV file on disk."""
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "product,price,quantity\n"
        "Widget A,29.99,100\n"
        "Widget B,49.99,50\n"
        "Widget C,19.99,200\n"
    )
    return Dataset(
        id=1,
        user_id=1,
        name="products.csv",
        file_type="csv",
        file_path=str(csv_path),
        file_size_bytes=csv_path.stat().st_size,
        row_count=3,
        column_count=3,
        columns_metadata=[
            {"name": "product", "dtype": "object", "sample_values": ["Widget A", "Widget B"]},
            {"name": "price", "dtype": "float64", "sample_values": ["29.99", "49.99"]},
            {"name": "quantity", "dtype": "int64", "sample_values": ["100", "50"]},
        ],
    )


class TestExecuteQuery:
    """Tests for real DuckDB execution against a dataset file."""

    def test_executes_simple_select(self, sample_dataset: Dataset):
        columns, rows, row_count, elapsed_ms = SQLEngineService.execute_query(
            sample_dataset, "SELECT product, price FROM dataset ORDER BY price DESC"
        )
        assert columns == ["product", "price"]
        assert row_count == 3
        assert rows[0][0] == "Widget B"  # highest price
        assert elapsed_ms >= 0

    def test_executes_aggregate_query(self, sample_dataset: Dataset):
        columns, rows, row_count, _ = SQLEngineService.execute_query(
            sample_dataset, "SELECT COUNT(*) AS total, AVG(price) AS avg_price FROM dataset"
        )
        assert columns == ["total", "avg_price"]
        assert row_count == 1
        assert rows[0][0] == 3

    def test_rejects_non_select_before_execution(self, sample_dataset: Dataset):
        with pytest.raises(SQLValidationError, match="Only SELECT queries"):
            SQLEngineService.execute_query(sample_dataset, "DROP TABLE dataset")

    def test_rejects_unstructured_file_type(self, sample_dataset: Dataset):
        sample_dataset.file_type = "pdf"
        with pytest.raises(SQLValidationError, match="Cannot run SQL"):
            SQLEngineService.execute_query(sample_dataset, "SELECT * FROM dataset")

    def test_missing_file_raises_clear_error(self, sample_dataset: Dataset):
        sample_dataset.file_path = "/nonexistent/path/file.csv"
        with pytest.raises(SQLValidationError, match="not found"):
            SQLEngineService.execute_query(sample_dataset, "SELECT * FROM dataset")

    def test_row_cap_is_enforced(self, sample_dataset: Dataset, monkeypatch):
        """Even if the LLM's SQL has no LIMIT, results are capped server-side."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "SQL_MAX_ROWS", 2)

        columns, rows, row_count, _ = SQLEngineService.execute_query(
            sample_dataset, "SELECT * FROM dataset"
        )
        assert row_count == 2  # capped from 3 to 2


class TestBuildSchemaContext:
    """Tests for the schema description sent to the LLM."""

    def test_includes_table_name_and_columns(self, sample_dataset: Dataset):
        context = SQLEngineService.build_schema_context(sample_dataset)
        assert '"dataset"' in context
        assert '"product"' in context
        assert '"price"' in context
        assert '"quantity"' in context

    def test_raises_when_no_column_metadata(self, sample_dataset: Dataset):
        sample_dataset.columns_metadata = None
        with pytest.raises(SQLValidationError, match="no column metadata"):
            SQLEngineService.build_schema_context(sample_dataset)


# ─── Full Endpoint Integration Tests (LLM mocked) ──────────────

SAMPLE_CSV = (
    "product,price,quantity\n"
    "Widget A,29.99,100\n"
    "Widget B,49.99,50\n"
    "Widget C,19.99,200\n"
)


async def _upload_sample_dataset(client: AsyncClient, auth_headers: dict) -> int:
    """Helper: upload a small CSV and return its dataset_id."""
    import io
    files = {"file": ("products.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    response = await client.post("/api/v1/data/upload", files=files, headers=auth_headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_ask_question_success(client: AsyncClient, auth_headers: dict):
    """Full pipeline with mocked LLM: question -> SQL -> execution -> explanation."""
    dataset_id = await _upload_sample_dataset(client, auth_headers)

    # Mock the two LLM calls: first returns SQL, second returns an explanation
    with patch(
        "app.services.llm_service.LLMService.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.side_effect = [
            'SELECT product, price FROM dataset ORDER BY price DESC LIMIT 1',
            "Widget B is the most expensive product at $49.99.",
        ]

        response = await client.post(
            "/api/v1/sql/query",
            json={"dataset_id": dataset_id, "question": "What is the most expensive product?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 1
    assert data["rows"][0][0] == "Widget B"
    assert "Widget B" in data["explanation"]
    assert "SELECT" in data["sql"].upper()


@pytest.mark.asyncio
async def test_ask_question_strips_markdown_fences(client: AsyncClient, auth_headers: dict):
    """If the LLM wraps SQL in ```sql fences despite instructions, we should still handle it."""
    dataset_id = await _upload_sample_dataset(client, auth_headers)

    with patch(
        "app.services.llm_service.LLMService.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.side_effect = [
            "```sql\nSELECT * FROM dataset\n```",
            "There are 3 products.",
        ]

        response = await client.post(
            "/api/v1/sql/query",
            json={"dataset_id": dataset_id, "question": "How many products are there?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 3
    assert not data["sql"].startswith("```")


@pytest.mark.asyncio
async def test_ask_question_rejects_unsafe_generated_sql(client: AsyncClient, auth_headers: dict):
    """If the LLM generates unsafe SQL, the endpoint returns 422, not a 500 or silent execution."""
    dataset_id = await _upload_sample_dataset(client, auth_headers)

    with patch(
        "app.services.llm_service.LLMService.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.return_value = "DROP TABLE dataset"

        response = await client.post(
            "/api/v1/sql/query",
            json={"dataset_id": dataset_id, "question": "Delete everything"},
            headers=auth_headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ask_question_nonexistent_dataset(client: AsyncClient, auth_headers: dict):
    """404 for a dataset that doesn't exist or isn't owned by the user."""
    response = await client.post(
        "/api/v1/sql/query",
        json={"dataset_id": 99999, "question": "Anything"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ask_question_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/sql/query",
        json={"dataset_id": 1, "question": "Anything"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_failed_query_is_logged(client: AsyncClient, auth_headers: dict):
    """Failed NL2SQL attempts should still appear in the query history log."""
    dataset_id = await _upload_sample_dataset(client, auth_headers)

    with patch(
        "app.services.llm_service.LLMService.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.return_value = "DELETE FROM dataset"

        await client.post(
            "/api/v1/sql/query",
            json={"dataset_id": dataset_id, "question": "Delete everything"},
            headers=auth_headers,
        )

    history_response = await client.get(
        f"/api/v1/sql/history?dataset_id={dataset_id}",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["total"] == 1
    assert history["logs"][0]["success"] is False
    assert history["logs"][0]["error_message"] is not None


@pytest.mark.asyncio
async def test_successful_query_appears_in_history(client: AsyncClient, auth_headers: dict):
    dataset_id = await _upload_sample_dataset(client, auth_headers)

    with patch(
        "app.services.llm_service.LLMService.complete",
        new_callable=AsyncMock,
    ) as mock_complete:
        mock_complete.side_effect = [
            "SELECT * FROM dataset",
            "There are 3 products in this dataset.",
        ]
        await client.post(
            "/api/v1/sql/query",
            json={"dataset_id": dataset_id, "question": "Show everything"},
            headers=auth_headers,
        )

    history_response = await client.get("/api/v1/sql/history", headers=auth_headers)
    history = history_response.json()
    assert history["total"] == 1
    assert history["logs"][0]["success"] is True
    assert history["logs"][0]["row_count"] == 3
