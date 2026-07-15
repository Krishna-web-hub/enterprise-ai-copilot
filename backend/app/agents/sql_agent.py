"""
SQL Agent

Handles data questions by calling NL2SQLService against the user's datasets.
If multiple datasets exist, picks the most relevant one based on the instruction.
If only one exists, uses it directly.
"""

from app.agents.state import AgentState
from app.services.llm_service import LLMServiceError
from app.services.nl2sql_service import NL2SQLService
from app.services.sql_engine_service import SQLValidationError


async def sql_agent_node(state: AgentState, instruction: str, db) -> dict:
    """
    Execute a SQL query against the user's data.

    Returns: {agent, instruction, result, success}
    """
    datasets = state.get("available_datasets", [])
    user_id = state["user_id"]

    if not datasets:
        return {
            "agent": "sql_agent",
            "instruction": instruction,
            "result": "No structured datasets are available to query. Please upload a CSV, Excel, or JSON file first.",
            "success": False,
        }

    # Pick the first dataset (in a more advanced version, the planner's
    # instruction would specify which dataset, or we'd use semantic matching)
    # For now, use the most recently uploaded structured dataset.
    structured = [d for d in datasets if d.get("file_type") in ("csv", "excel", "json")]
    if not structured:
        return {
            "agent": "sql_agent",
            "instruction": instruction,
            "result": "No queryable structured datasets found (need CSV, Excel, or JSON).",
            "success": False,
        }

    target_dataset_info = structured[0]

    # We need to load the actual Dataset ORM object for NL2SQLService
    from app.services.data_service import DataService
    data_service = DataService(db)
    dataset = await data_service.get_dataset(target_dataset_info["id"], user_id)

    if not dataset:
        return {
            "agent": "sql_agent",
            "instruction": instruction,
            "result": "Could not load the target dataset.",
            "success": False,
        }

    nl2sql = NL2SQLService(db)
    try:
        result = await nl2sql.ask(dataset, instruction, user_id)
        # Format a readable text response
        answer_parts = []
        if result.get("explanation"):
            answer_parts.append(result["explanation"])
        if result.get("sql"):
            answer_parts.append(f"\nSQL: `{result['sql']}`")
        if result.get("row_count") is not None:
            answer_parts.append(f"({result['row_count']} rows returned)")

        return {
            "agent": "sql_agent",
            "instruction": instruction,
            "result": "\n".join(answer_parts),
            "success": True,
            "data": result,  # Raw data for potential further processing
        }
    except (SQLValidationError, LLMServiceError) as e:
        return {
            "agent": "sql_agent",
            "instruction": instruction,
            "result": f"SQL query failed: {str(e)}",
            "success": False,
        }
