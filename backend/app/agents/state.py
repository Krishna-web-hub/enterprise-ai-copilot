"""
Agent State Definition

The TypedDict that flows through the LangGraph state machine.
Every node in the graph reads from and writes to this shared state.

Why a TypedDict rather than a Pydantic model?
- LangGraph's StateGraph requires TypedDict (or dataclass) for state
- Pydantic adds serialization overhead that isn't needed for in-process state
- TypedDict gives us type hints without runtime validation cost
"""

from typing import TypedDict


class PlanStep(TypedDict):
    """A single step in the execution plan produced by the Planner."""
    agent: str  # "sql_agent", "rag_agent", "ml_agent", "vision_agent", "general"
    instruction: str  # What to tell this agent to do


class AgentState(TypedDict, total=False):
    """
    The shared state that flows through the agentic pipeline.

    Fields are added/updated by different nodes:
    - question, user_id, context: set at the start
    - plan: set by the Planner node
    - step_results: accumulated by each agent node
    - final_answer: set by the Synthesizer node
    - metadata: accumulated throughout for debugging/UI display
    """
    # Input (set at start)
    question: str
    user_id: int
    session_id: int

    # Context about what the user has (for the Planner to know what's available)
    available_datasets: list[dict]  # [{id, name, file_type, row_count, column_count}]
    available_documents: list[dict]  # [{id, name, file_type, embedding_status}]
    available_models: list[dict]  # [{id, name, model_type, algorithm}]

    # Plan (set by Planner)
    plan: list[PlanStep]
    plan_reasoning: str

    # Execution (accumulated by agent nodes)
    current_step_index: int
    step_results: list[dict]  # [{agent, instruction, result, success}]

    # Output (set by Synthesizer)
    final_answer: str

    # Metadata for UI (agent logs)
    metadata: dict  # {agents_used, total_time_ms, plan, etc.}
