"""
General Agent

Handles questions that don't need a specialized tool — general explanations,
summarization of prior step results, or questions outside the platform's
data scope. Uses the LLM directly.
"""

from app.agents.state import AgentState
from app.services.llm_service import LLMService, LLMServiceError

GENERAL_SYSTEM_PROMPT = """You are a helpful AI assistant within an enterprise analytics platform. \
You help users understand their data, explain findings, and provide business insights.

If previous analysis results are provided as context, incorporate them into your response. \
Be concise, specific, and actionable. Speak in business terms, not technical jargon.

Use markdown formatting in your responses: **bold** for emphasis, numbered lists for steps, \
bullet points for options. Use relevant emojis to make responses more engaging and scannable \
(e.g. 📊 for data, 🔍 for analysis, ✅ for success, ⚠️ for warnings, 💡 for tips, 🚀 for actions)."""


async def general_agent_node(state: AgentState, instruction: str, db) -> dict:
    """
    Handle general questions or synthesize results from prior steps.

    If previous step_results exist, they're included as context so the
    General Agent can summarize or build on them.

    Returns: {agent, instruction, result, success}
    """
    step_results = state.get("step_results", [])

    # Build context from any prior step results
    context_parts = []
    for sr in step_results:
        if sr.get("success") and sr.get("result"):
            context_parts.append(f"[{sr['agent']}]: {sr['result']}")

    if context_parts:
        context = "Previous analysis results:\n" + "\n\n".join(context_parts)
        user_prompt = f"{context}\n\nUser question/instruction: {instruction}"
    else:
        user_prompt = instruction

    llm = LLMService()
    try:
        answer = await llm.complete(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=800,
            temperature=0.3,
        )
        return {
            "agent": "general",
            "instruction": instruction,
            "result": answer,
            "success": True,
        }
    except LLMServiceError as e:
        return {
            "agent": "general",
            "instruction": instruction,
            "result": f"I wasn't able to generate a response: {str(e)}",
            "success": False,
        }
