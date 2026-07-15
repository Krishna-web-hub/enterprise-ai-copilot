"""
ML Agent

Handles machine learning questions: reports on trained model metrics,
feature importance, and can describe what models are available.
(Running actual predictions requires specific input data which is
better handled through the Models UI; this agent reports insights.)
"""

from app.agents.state import AgentState


async def ml_agent_node(state: AgentState, instruction: str, db) -> dict:
    """
    Provide ML model insights and information.

    Returns: {agent, instruction, result, success}
    """
    models = state.get("available_models", [])
    user_id = state["user_id"]

    if not models:
        return {
            "agent": "ml_agent",
            "instruction": instruction,
            "result": "No trained ML models are available. Train a model in the Models section first.",
            "success": False,
        }

    # Build a summary of available models and their key metrics
    from app.services.ml_service import MLService
    ml_service = MLService(db)

    summaries = []
    for model_info in models[:5]:
        model = await ml_service.get_model(model_info["id"], user_id)
        if model:
            metrics_str = ", ".join(f"{k}: {v}" for k, v in (model.metrics or {}).items())
            importance_str = ""
            if model.feature_importance:
                top_features = list(model.feature_importance.keys())[:3]
                importance_str = f" | Top features: {', '.join(top_features)}"

            summaries.append(
                f"• {model.name} ({model.model_type}, {model.algorithm}): {metrics_str}{importance_str}"
            )

    result_text = "Available ML models:\n" + "\n".join(summaries)
    result_text += f"\n\nRegarding your question: '{instruction}' — "

    # Provide relevant insight based on what models exist
    if any("classification" in m.get("model_type", "") for m in models):
        result_text += "Classification models can predict categories (e.g. churn yes/no). "
    if any("regression" in m.get("model_type", "") for m in models):
        result_text += "Regression models can forecast numerical values. "
    result_text += "Use the Models page to run predictions with specific input data."

    return {
        "agent": "ml_agent",
        "instruction": instruction,
        "result": result_text,
        "success": True,
    }
