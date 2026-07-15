"""
Agent Orchestrator

The execution engine that runs the Planner → Agent(s) → Synthesize pipeline.

Architecture:
1. Build initial state with user context (datasets, documents, models)
2. Run the Planner node to produce an execution plan
3. Execute each plan step sequentially, routing to the correct agent
4. Synthesize the final answer from all step results

Why not use LangGraph's StateGraph directly for the full loop?
- Our agent nodes need a SQLAlchemy async session (`db`) which doesn't
  fit cleanly into LangGraph's state dict (not serializable, not
  passable between separate process-based nodes)
- The sequential plan execution is a simple loop that doesn't benefit
  from LangGraph's parallel/conditional branching features
- We DO use LangGraph's conceptual model (state machine with typed state),
  just implement the execution loop ourselves for practical reasons

This orchestrator is what ChatService.process_user_message() calls.
It returns the final answer + metadata for the chat message response.
"""

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.general_agent import general_agent_node
from app.agents.ml_agent import ml_agent_node
from app.agents.planner import planner_node
from app.agents.rag_agent import rag_agent_node
from app.agents.sql_agent import sql_agent_node
from app.agents.state import AgentState
from app.agents.vision_agent import vision_agent_node
from app.models.dataset import Dataset
from app.models.document import Document
from app.models.ml_model import MLModel

# Agent dispatch map
AGENT_REGISTRY = {
    "sql_agent": sql_agent_node,
    "rag_agent": rag_agent_node,
    "ml_agent": ml_agent_node,
    "vision_agent": vision_agent_node,
    "general": general_agent_node,
}


class AgentOrchestrator:
    """
    Runs the full agentic pipeline for a user message.

    Usage:
        orchestrator = AgentOrchestrator(db)
        result = await orchestrator.run(question="Why are sales declining?", user_id=1)
        # result = {"answer": "...", "metadata": {...}}
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, question: str, user_id: int, session_id: int = 0) -> dict:
        """
        Execute the full Planner → Agents → Synthesize pipeline.

        Args:
            question: The user's natural-language message
            user_id: The authenticated user's ID
            session_id: The chat session ID (for context)

        Returns:
            {
                "answer": str,  # The final synthesized response
                "metadata": {
                    "plan_reasoning": str,
                    "plan_steps": list,
                    "agents_used": list[str],
                    "step_results": list[dict],
                    "total_time_ms": int,
                }
            }
        """
        start_time = time.monotonic()

        # Step 1: Build context — what resources does this user have?
        context = await self._build_user_context(user_id)

        # Step 2: Initialize state
        state: AgentState = {
            "question": question,
            "user_id": user_id,
            "session_id": session_id,
            "available_datasets": context["datasets"],
            "available_documents": context["documents"],
            "available_models": context["models"],
            "plan": [],
            "plan_reasoning": "",
            "current_step_index": 0,
            "step_results": [],
            "final_answer": "",
            "metadata": {},
        }

        # Step 3: Run the Planner
        plan_updates = await planner_node(state)
        state.update(plan_updates)

        # Step 4: Execute each plan step sequentially
        for i, step in enumerate(state["plan"]):
            state["current_step_index"] = i
            agent_name = step["agent"]
            instruction = step["instruction"]

            agent_fn = AGENT_REGISTRY.get(agent_name)
            if agent_fn is None:
                # Unknown agent — fall back to general
                agent_fn = general_agent_node

            step_result = await agent_fn(state, instruction, self.db)
            state["step_results"].append(step_result)

        # Step 5: Synthesize final answer
        final_answer = self._synthesize_answer(state)
        state["final_answer"] = final_answer

        total_time_ms = int((time.monotonic() - start_time) * 1000)

        metadata = {
            "plan_reasoning": state.get("plan_reasoning", ""),
            "plan_steps": [dict(s) for s in state.get("plan", [])],
            "agents_used": [sr["agent"] for sr in state["step_results"]],
            "step_results": [
                {"agent": sr["agent"], "success": sr["success"]}
                for sr in state["step_results"]
            ],
            "total_time_ms": total_time_ms,
        }

        return {"answer": final_answer, "metadata": metadata}

    async def _build_user_context(self, user_id: int) -> dict:
        """
        Load summary info about the user's available resources.
        This gives the Planner the context it needs to decide which agents
        can actually help (e.g. don't route to SQL agent if no datasets exist).
        """
        # Datasets
        ds_result = await self.db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
            .limit(10)
        )
        datasets = [
            {
                "id": d.id,
                "name": d.name,
                "file_type": d.file_type,
                "row_count": d.row_count,
                "column_count": d.column_count,
            }
            for d in ds_result.scalars().all()
        ]

        # Documents
        doc_result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(10)
        )
        documents = [
            {
                "id": d.id,
                "name": d.name,
                "file_type": d.file_type,
                "embedding_status": d.embedding_status,
            }
            for d in doc_result.scalars().all()
        ]

        # ML Models
        model_result = await self.db.execute(
            select(MLModel)
            .where(MLModel.user_id == user_id)
            .order_by(MLModel.created_at.desc())
            .limit(10)
        )
        models = [
            {
                "id": m.id,
                "name": m.name,
                "model_type": m.model_type,
                "algorithm": m.algorithm,
            }
            for m in model_result.scalars().all()
        ]

        return {"datasets": datasets, "documents": documents, "models": models}

    @staticmethod
    def _synthesize_answer(state: AgentState) -> str:
        """
        Produce the final answer from accumulated step results.

        Strategy:
        - If there's only one step result, use it directly
        - If there are multiple results, combine them with clear separation
        - If all steps failed, provide a helpful fallback message
        """
        results = state.get("step_results", [])

        if not results:
            return "I wasn't able to process your question. Please try rephrasing it."

        successful_results = [r for r in results if r.get("success")]

        if not successful_results:
            # All steps failed — return the first error
            first_error = results[0].get("result", "Something went wrong.")
            return first_error

        if len(successful_results) == 1:
            return successful_results[0]["result"]

        # Multiple successful results — combine them
        parts = []
        for r in successful_results:
            parts.append(r["result"])

        return "\n\n---\n\n".join(parts)
