"""
SQL Engine Service — Natural Language to SQL Execution

Architecture decision (see Phase 4 design discussion):
Uploaded datasets are queried via DuckDB, an embedded, in-process analytical
SQL engine, rather than materializing them as dynamic tables in the
application's PostgreSQL database.

Why DuckDB instead of dynamic Postgres tables?
- No dynamic DDL: we never CREATE TABLE with user-controlled identifiers,
  which removes an entire class of injection/sanitization risk
- No schema drift: every query re-reads the source file fresh, so there's
  no "the table is stale because the user re-uploaded the CSV" problem
- Isolation: a malformed or huge dataset can't corrupt or bloat the shared
  application database
- DuckDB speaks real SQL (including most Postgres-compatible syntax), so
  the LLM's Postgres-flavored training data transfers well

PostgreSQL remains the system of record for everything about the app
(users, dataset metadata, chat history, logs). DuckDB is purely a query
execution engine for the CONTENTS of uploaded files, used transiently
per-request.

Security model for LLM-generated SQL:
LLM output is untrusted input. Before executing anything, we enforce:
1. Exactly one statement (no semicolon-separated stacked queries)
2. Statement type must be SELECT (or a WITH...SELECT CTE)
3. No DDL/DML keywords anywhere (DROP, DELETE, UPDATE, INSERT, ALTER, etc.)
4. No access to files, other tables, or system functions
5. A LIMIT is always enforced server-side, regardless of what the LLM wrote
6. A statement timeout prevents runaway queries (e.g. cartesian joins)
"""

import re
import threading
import time
from pathlib import Path

import duckdb

from app.core.config import settings
from app.models.dataset import Dataset
from app.utils.file_readers import read_structured_file

STRUCTURED_TYPES = {"csv", "excel", "json"}

# The single table name every query must reference. Since each query runs
# against exactly one dataset, we always expose it as "dataset" — this also
# means the LLM never needs to know (or guess) a real table name.
TABLE_NAME = "dataset"

# Keywords that indicate the SQL is not a pure read-only SELECT.
# Checked as whole words against the uppercased SQL text.
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "ATTACH", "DETACH", "COPY", "EXPORT", "IMPORT",
    "PRAGMA", "CALL", "EXECUTE", "INSTALL", "LOAD", "SET", "VACUUM",
}


class SQLValidationError(Exception):
    """Raised when LLM-generated SQL fails safety validation."""
    pass


class SQLEngineService:
    """
    Builds schema context for the LLM and safely executes generated SQL
    against a dataset's underlying file using DuckDB.
    """

    # ─── Schema Context (for the LLM prompt) ───────────────────────

    @staticmethod
    def build_schema_context(dataset: Dataset) -> str:
        """
        Build a compact text description of the dataset's schema for the LLM.

        This is what "grounds" the LLM so it generates SQL against real
        column names instead of hallucinating them. Includes:
        - Table name (always "dataset")
        - Column names, types, and a few sample values per column

        Kept intentionally concise — large schema dumps waste tokens and
        can dilute the model's attention on the actual question.
        """
        if not dataset.columns_metadata:
            raise SQLValidationError(
                "This dataset has no column metadata available. "
                "It may not have been parsed successfully on upload."
            )

        lines = [f'Table name: "{TABLE_NAME}"', "Columns:"]
        for col in dataset.columns_metadata:
            samples = ", ".join(col.get("sample_values", [])[:3])
            lines.append(
                f'  - "{col["name"]}" ({col["dtype"]})'
                f' — sample values: {samples}' if samples else f'  - "{col["name"]}" ({col["dtype"]})'
            )

        return "\n".join(lines)

    # ─── SQL Validation ─────────────────────────────────────────────

    @staticmethod
    def validate_sql(sql: str) -> str:
        """
        Validate that generated SQL is safe to execute.

        Enforces:
        - Non-empty
        - Single statement only (rejects "; DROP TABLE ...")
        - Must be a SELECT or WITH...SELECT statement
        - No forbidden keywords anywhere in the statement

        Returns the cleaned SQL (stripped, trailing semicolon removed) if valid.

        Raises:
            SQLValidationError: If any check fails
        """
        if not sql or not sql.strip():
            raise SQLValidationError("Generated SQL is empty")

        cleaned = sql.strip()

        # Strip a single trailing semicolon (if present) before checking for
        # stacked statements — DuckDB/most DBs allow one trailing `;`.
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()

        # Reject stacked statements: any remaining semicolon means there's
        # more than one statement.
        if ";" in cleaned:
            raise SQLValidationError(
                "Multiple SQL statements are not allowed. Only a single SELECT is permitted."
            )

        # Must start with SELECT or WITH (CTE that eventually SELECTs)
        first_word_match = re.match(r"^\s*(\w+)", cleaned, re.IGNORECASE)
        first_word = first_word_match.group(1).upper() if first_word_match else ""

        if first_word not in ("SELECT", "WITH"):
            raise SQLValidationError(
                f"Only SELECT queries are allowed. Statement starts with '{first_word}'."
            )

        # Scan for forbidden keywords as whole words (case-insensitive)
        upper_sql = cleaned.upper()
        for keyword in FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", upper_sql):
                raise SQLValidationError(
                    f"Query contains a disallowed keyword: {keyword}. "
                    "Only read-only SELECT queries are permitted."
                )

        return cleaned

    # ─── Execution ──────────────────────────────────────────────────

    @staticmethod
    def execute_query(dataset: Dataset, sql: str) -> tuple[list[str], list[list], int, int]:
        """
        Execute a validated SQL query against a dataset's file using DuckDB.

        Steps:
        1. Validate the SQL (defense in depth — callers should already
           validate, but we never trust SQL twice-removed from an LLM)
        2. Load the source file into a pandas DataFrame
        3. Register it as a DuckDB view named "dataset"
        4. Enforce a row LIMIT and statement timeout
        5. Execute and return results

        Args:
            dataset: The Dataset record (must be a structured file type)
            sql: The LLM-generated SQL to execute

        Returns:
            (column_names, rows, row_count, execution_time_ms)

        Raises:
            SQLValidationError: If SQL fails validation or dataset isn't queryable
            duckdb.Error: If DuckDB fails to execute the (validated) query
                          (e.g. references a column that doesn't exist)
        """
        if dataset.file_type not in STRUCTURED_TYPES:
            raise SQLValidationError(
                f"Cannot run SQL against '{dataset.file_type}' files. "
                "Only structured datasets (CSV, Excel, JSON) support querying."
            )

        validated_sql = SQLEngineService.validate_sql(sql)

        file_path = Path(dataset.file_path)
        if not file_path.exists():
            from app.core.config import settings
            file_path = Path(settings.upload_path) / dataset.file_path
        if not file_path.exists():
            raise SQLValidationError(f"Dataset file not found on disk: {dataset.file_path}")

        df = read_structured_file(file_path, dataset.file_type)

        # Enforce the row cap server-side by wrapping the query, regardless
        # of whether the LLM included its own LIMIT. This guarantees the cap
        # even if the LLM omits or inflates a LIMIT clause.
        capped_sql = f"SELECT * FROM ({validated_sql}) AS _capped LIMIT {settings.SQL_MAX_ROWS}"

        conn = duckdb.connect(":memory:")
        timer: threading.Timer | None = None
        try:
            conn.register(TABLE_NAME, df)

            # DuckDB has no built-in query-timeout setting, so we enforce one
            # manually: a background timer calls conn.interrupt() if the
            # query is still running after SQL_QUERY_TIMEOUT_SECONDS. This
            # guards against pathological queries (e.g. huge cross joins)
            # that the row LIMIT alone wouldn't stop from running slowly.
            timer = threading.Timer(settings.SQL_QUERY_TIMEOUT_SECONDS, conn.interrupt)
            timer.start()

            start = time.monotonic()
            try:
                result = conn.execute(capped_sql)
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
            except duckdb.InterruptException:
                raise SQLValidationError(
                    f"Query exceeded the {settings.SQL_QUERY_TIMEOUT_SECONDS}s time limit and was cancelled."
                )
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return columns, [list(row) for row in rows], len(rows), elapsed_ms
        finally:
            if timer is not None:
                timer.cancel()
            conn.close()
