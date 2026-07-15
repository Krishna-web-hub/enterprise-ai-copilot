"""
RAG Agent

Handles document questions by calling RAGService to retrieve relevant
chunks and generate a cited answer.
"""

from app.agents.state import AgentState
from app.services.rag_service import RAGService, RAGServiceError


async def rag_agent_node(state: AgentState, instruction: str, db) -> dict:
    """
    Answer a question using document context (RAG).

    Returns: {agent, instruction, result, success}
    """
    documents = state.get("available_documents", [])
    user_id = state["user_id"]

    # Check if any documents are ingested and ready
    ready_docs = [d for d in documents if d.get("embedding_status") == "completed"]
    if not ready_docs:
        return {
            "agent": "rag_agent",
            "instruction": instruction,
            "result": "No documents have been ingested for Q&A yet. Upload a PDF, Word, or text file in the Documents section first.",
            "success": False,
        }

    rag_service = RAGService(db)
    try:
        result = await rag_service.query(question=instruction, user_id=user_id, top_k=5)
        answer = result["answer"]

        # Append source references for context
        if result["sources"]:
            sources_text = "\n\nSources:\n"
            for s in result["sources"]:
                page_info = f", page {s['page_number']}" if s.get("page_number") else ""
                sources_text += f"  [{s['source_number']}] {s['document_name']}{page_info}\n"
            answer += sources_text

        return {
            "agent": "rag_agent",
            "instruction": instruction,
            "result": answer,
            "success": True,
        }
    except RAGServiceError as e:
        return {
            "agent": "rag_agent",
            "instruction": instruction,
            "result": f"Document search failed: {str(e)}",
            "success": False,
        }
