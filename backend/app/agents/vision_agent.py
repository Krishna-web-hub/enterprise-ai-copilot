"""
Vision Agent

Handles image/document analysis questions by calling VisionService.
Picks the most recently uploaded image or PDF dataset to analyze.
"""

from app.agents.state import AgentState
from app.services.vision_service import VisionService, VisionServiceError


async def vision_agent_node(state: AgentState, instruction: str, db) -> dict:
    """
    Analyze an image or PDF using deep learning models.

    Returns: {agent, instruction, result, success}
    """
    datasets = state.get("available_datasets", [])
    user_id = state["user_id"]

    # Find image/pdf datasets
    vision_datasets = [d for d in datasets if d.get("file_type") in ("image", "pdf")]
    if not vision_datasets:
        return {
            "agent": "vision_agent",
            "instruction": instruction,
            "result": "No image or PDF files have been uploaded. Upload an image or PDF in the Datasets section first.",
            "success": False,
        }

    target_info = vision_datasets[0]  # Most recent

    # Load the actual Dataset ORM object
    from app.services.data_service import DataService
    data_service = DataService(db)
    dataset = await data_service.get_dataset(target_info["id"], user_id)

    if not dataset:
        return {
            "agent": "vision_agent",
            "instruction": instruction,
            "result": "Could not load the target image/PDF.",
            "success": False,
        }

    vision_service = VisionService()
    try:
        results = await vision_service.analyze(
            dataset=dataset,
            modes=["all"],
            top_k=5,
            confidence_threshold=0.4,
        )

        # Format results into readable text
        parts = []

        if "classification" in results:
            preds = results["classification"]["predictions"]
            if preds:
                labels = ", ".join(f"{p['label']} ({p['confidence']:.0%})" for p in preds[:3])
                parts.append(f"Image classification: {labels}")

        if "detection" in results:
            dets = results["detection"]["detections"]
            if dets:
                objects = ", ".join(f"{d['label']} ({d['confidence']:.0%})" for d in dets[:5])
                parts.append(f"Objects detected: {objects}")
            else:
                parts.append("No objects detected above confidence threshold.")

        if "ocr" in results:
            text = results["ocr"].get("text", "")
            if text:
                preview = text[:300] + ("..." if len(text) > 300 else "")
                parts.append(f"Extracted text: \"{preview}\"")
            else:
                parts.append("No text found in the image.")

        result_text = "\n".join(parts) if parts else "Analysis complete but no notable results."

        return {
            "agent": "vision_agent",
            "instruction": instruction,
            "result": result_text,
            "success": True,
        }
    except VisionServiceError as e:
        return {
            "agent": "vision_agent",
            "instruction": instruction,
            "result": f"Vision analysis failed: {str(e)}",
            "success": False,
        }
