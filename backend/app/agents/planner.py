"""
Planner Agent

The "brain" of the agentic system. Receives the user's question plus
context about what resources are available (datasets, documents, models),
and outputs a structured execution plan.

The Planner does NOT execute anything — it only decides WHAT to do and
in WHAT ORDER. The orchestrator then executes the plan step by step.

Why a separate Planner instead of a single monolithic agent?
- Separation of concerns: planning is a different skill than execution
- Inspectability: users can see the plan before/while it executes
- Testability: we can test planning logic independently from agent execution
- Correctness: explicit plans avoid the "agent wanders off" problem where
  a single ReAct loop makes progressively worse decisions
"""

from app.agents.state import AgentState, PlanStep
from app.services.llm_service import LLMService, LLMServiceError

PLANNER_SYSTEM_PROMPT = """You are an AI planning assistant for a data analytics platform. \
Your job is to analyze the user's question and decide which specialized agents should handle it.

Available agents:
- sql_agent: Queries structured datasets (CSV/Excel/JSON) using natural language to SQL. \
Use when the user asks data questions like "show top products", "average sales", "filter by X".
- rag_agent: Answers questions from uploaded documents (PDF/Word/text) with citations. \
Use when the user asks about document content like policies, contracts, reports.
- ml_agent: Provides insights from trained ML models (predictions, feature importance, metrics). \
Use when the user asks about predictions, model performance, or what drives outcomes.
- vision_agent: Analyzes uploaded images (classification, object detection, OCR). \
Use when the user asks about image content or wants text extracted from images.
- general: Handles general questions, explanations, or summarization that don't need any specialized tool. \
Use when the user asks general knowledge questions or wants a summary of previous results.

Context provided:
- Available datasets (structured data the SQL agent can query)
- Available documents (documents the RAG agent can search)
- Available models (trained ML models)

Rules:
1. Output valid JSON with "reasoning" and "steps" fields.
2. Each step has "agent" (one of the agent names above) and "instruction" (what to tell that agent).
3. Use 1-3 steps maximum. Keep plans concise.
4. If no specialized agent is needed, use a single "general" step.
5. If the user's question requires data AND explanation, use sql_agent first, then general to summarize.
6. If no relevant datasets/documents/models exist for the question, use "general" to explain what's needed.

Output format (JSON only, no markdown):
{"reasoning": "...", "steps": [{"agent": "...", "instruction": "..."}, ...]}
"""


async def planner_node(state: AgentState) -> dict:
    """
    LangGraph node: Analyze the question and produce an execution plan.

    Reads: question, available_datasets, available_documents, available_models
    Writes: plan, plan_reasoning, current_step_index, step_results, metadata
    """
    question = state["question"]
    datasets = state.get("available_datasets", [])
    documents = state.get("available_documents", [])
    models = state.get("available_models", [])

    # Build context string for the planner
    context_parts = []
    if datasets:
        ds_list = ", ".join(f'"{d["name"]}" ({d.get("row_count", "?")} rows)' for d in datasets[:5])
        context_parts.append(f"Available datasets: {ds_list}")
    else:
        context_parts.append("Available datasets: none")

    if documents:
        doc_list = ", ".join(f'"{d["name"]}" ({d.get("embedding_status", "?")})' for d in documents[:5])
        context_parts.append(f"Available documents: {doc_list}")
    else:
        context_parts.append("Available documents: none")

    if models:
        model_list = ", ".join(f'"{m["name"]}" ({m.get("model_type", "?")})' for m in models[:5])
        context_parts.append(f"Available models: {model_list}")
    else:
        context_parts.append("Available models: none")

    context_str = "\n".join(context_parts)
    user_prompt = f"Context:\n{context_str}\n\nUser question: {question}"

    llm = LLMService()

    try:
        result = await llm.complete_json(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=500,
        )

        reasoning = result.get("reasoning", "No reasoning provided")
        raw_steps = result.get("steps", [])

        # Validate and sanitize steps
        valid_agents = {"sql_agent", "rag_agent", "ml_agent", "vision_agent", "general"}
        steps: list[PlanStep] = []
        for step in raw_steps[:3]:  # Cap at 3 steps
            agent = step.get("agent", "general")
            instruction = step.get("instruction", question)
            if agent not in valid_agents:
                agent = "general"
            steps.append(PlanStep(agent=agent, instruction=instruction))

        if not steps:
            steps = [PlanStep(agent="general", instruction=question)]

    except LLMServiceError:
        # If the LLM fails, fall back to a simple general response
        reasoning = "LLM planning failed, falling back to general agent"
        steps = [PlanStep(agent="general", instruction=question)]

    return {
        "plan": steps,
        "plan_reasoning": reasoning,
        "current_step_index": 0,
        "step_results": [],
        "metadata": {"plan_reasoning": reasoning, "plan_steps": steps},
    }
