"""
NL2SQL Orchestration Service

Ties together LLMService and SQLEngineService into the full pipeline:

    question + dataset
        │
        ▼
    build schema context (SQLEngineService)
        │
        ▼
    LLM call #1: question + schema → SQL (LLMService)
        │
        ▼
    validate + execute SQL (SQLEngineService)
        │
        ▼
    LLM call #2: question + results → explanation (LLMService)
        │
        ▼
    log the attempt (SQLQueryLog) regardless of outcome
        │
        ▼
    return structured result

Why a separate orchestration layer instead of putting this in the endpoint?
- This exact flow is what the future SQL Agent (Phase 8) will call as a tool.
  Keeping it in a service means the agent can invoke `NL2SQLService.ask()`
  directly without going through HTTP.
- Every attempt is logged here, in one place, regardless of which caller
  (REST endpoint today, agent tool later) triggers it.
"""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.sql_query_log import SQLQueryLog
from app.services.llm_service import LLMService, LLMServiceError
from app.services.sql_engine_service import SQLEngineService, SQLValidationError

# ─── Prompts ────────────────────────────────────────────────────────

SQL_GENERATION_SYSTEM_PROMPT = """You are an expert SQL analyst. Given a table schema and a business \
question, write a single DuckDB-compatible SQL SELECT statement that answers the question.

Rules:
- Output ONLY the SQL statement. No markdown, no code fences, no explanation.
- Use exactly one statement. Never use semicolons to chain multiple statements.
- Only generate SELECT (or WITH ... SELECT) statements. Never write INSERT, UPDATE, DELETE, DROP, \
ALTER, CREATE, or any other data-modifying statement.
- Reference only the table and columns given in the schema. Never invent column names.
- Always quote column and table names with double quotes to handle spaces/special characters, e.g. \
SELECT "column name" FROM "dataset".
- If the question cannot be answered with the given schema, still write your best-effort SQL query \
using the closest relevant columns.
- Include a reasonable LIMIT if the question implies "top N" or similar ranking.
"""

EXPLANATION_SYSTEM_PROMPT = """You are a business analyst explaining query results to a non-technical \
stakeholder. Given a question and the resulting data, write a concise 2-4 sentence explanation of what \
the data shows. Be specific with numbers. Do not repeat the raw data verbatim — synthesize an insight. \
Do not mention SQL, tables, or databases in your explanation — speak in business terms only."""


class NL2SQLService:
    """Orchestrates the full natural-language-to-SQL-to-explanation pipeline."""

    def __init__(self, db: AsyncSession, llm: LLMService | None = None):
        self.db = db
        self.llm = llm or LLMService()

    async def ask(self, dataset: Dataset, question: str, user_id: int) -> dict:
        """
        Run the full NL2SQL pipeline for a single question against a dataset.

        Always logs the attempt (success or failure) to SQLQueryLog.

        Returns:
            {
                "sql": str,
                "columns": list[str],
                "rows": list[list],
                "row_count": int,
                "explanation": str,
                "execution_time_ms": int,
            }

        Raises:
            SQLValidationError: If schema context is unavailable, generated SQL is
                                 unsafe, or execution fails
            LLMServiceError: If the LLM call fails (e.g. missing API key, rate limit)
        """
        start = time.monotonic()
        generated_sql: str | None = None

        try:
            # Step 1: Build schema context to ground the LLM
            schema_context = SQLEngineService.build_schema_context(dataset)

            # Step 2: LLM generates SQL from the question + schema
            user_prompt = f"Schema:\n{schema_context}\n\nQuestion: {question}"
            generated_sql = await self.llm.complete(
                system_prompt=SQL_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=500,
            )
            generated_sql = self._strip_markdown_fences(generated_sql)

            # Step 3: Validate + execute against DuckDB
            columns, rows, row_count, exec_ms = SQLEngineService.execute_query(dataset, generated_sql)

            # Step 4: LLM explains the results in business language
            explanation = await self._explain_results(question, columns, rows, row_count)

            total_ms = int((time.monotonic() - start) * 1000)

            # Step 5: Log success
            await self._log_attempt(
                user_id=user_id,
                dataset_id=dataset.id,
                question=question,
                generated_sql=generated_sql,
                explanation=explanation,
                row_count=row_count,
                execution_time_ms=total_ms,
                success=True,
                error_message=None,
            )

            return {
                "sql": generated_sql,
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "explanation": explanation,
                "execution_time_ms": total_ms,
            }

        except (SQLValidationError, LLMServiceError) as e:
            total_ms = int((time.monotonic() - start) * 1000)
            await self._log_attempt(
                user_id=user_id,
                dataset_id=dataset.id,
                question=question,
                generated_sql=generated_sql,
                explanation=None,
                row_count=None,
                execution_time_ms=total_ms,
                success=False,
                error_message=str(e),
            )
            raise

    async def _explain_results(
        self, question: str, columns: list[str], rows: list[list], row_count: int
    ) -> str:
        """
        Generate a natural-language explanation of query results.

        If the query returned zero rows, skip the LLM call — there's nothing
        to explain, and it avoids the model inventing a story about empty data.
        """
        if row_count == 0:
            return "No matching data was found for this question."

        # Cap how many rows we send to the explanation LLM call — we only
        # need enough to summarize, not the full result set (saves tokens
        # and avoids the model just restating a giant table).
        preview_rows = rows[:20]
        table_str = self._rows_to_text_table(columns, preview_rows)

        truncation_note = (
            f"\n(showing first 20 of {row_count} rows)" if row_count > 20 else ""
        )

        user_prompt = f"Question: {question}\n\nResults:\n{table_str}{truncation_note}"

        return await self.llm.complete(
            system_prompt=EXPLANATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=250,
        )

    async def _log_attempt(
        self,
        user_id: int,
        dataset_id: int,
        question: str,
        generated_sql: str | None,
        explanation: str | None,
        row_count: int | None,
        execution_time_ms: int | None,
        success: bool,
        error_message: str | None,
    ) -> SQLQueryLog:
        """Persist a record of this NL2SQL attempt for audit/debugging/dashboard use."""
        log = SQLQueryLog(
            user_id=user_id,
            dataset_id=dataset_id,
            question=question,
            generated_sql=generated_sql,
            explanation=explanation,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        # Commit immediately rather than just flushing. Audit log entries must
        # survive even when the overall request subsequently fails (e.g. the
        # endpoint raises an HTTPException after this). Since get_db() rolls
        # back the session on any exception that propagates out of the
        # request, a flush-only write would be discarded along with it.
        await self.db.commit()
        await self.db.refresh(log)
        return log

    @staticmethod
    def _strip_markdown_fences(sql: str) -> str:
        """
        Remove markdown code fences if the LLM wrapped its SQL in ```sql ... ```
        despite instructions not to. Defensive cleanup, not a security boundary
        (SQLEngineService.validate_sql still runs afterward regardless).
        """
        cleaned = sql.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Drop the opening fence line (```sql or ```)
            lines = lines[1:]
            # Drop the closing fence line if present
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    @staticmethod
    def _rows_to_text_table(columns: list[str], rows: list[list]) -> str:
        """Render rows as a simple pipe-delimited text table for the explanation prompt."""
        header = " | ".join(columns)
        separator = "-" * len(header)
        body_lines = [" | ".join(str(cell) for cell in row) for row in rows]
        return "\n".join([header, separator] + body_lines)
