"""
Agentic AI Module

Multi-agent orchestration layer that routes user questions to the
appropriate specialized agent(s) via a Planner → Execute → Synthesize
workflow built on LangGraph.

Agent roster:
- Planner: classifies intent, produces an ordered execution plan
- SQL Agent: answers data questions via NL2SQL (Phase 4)
- RAG Agent: answers document questions with citations (Phase 7)
- ML Agent: triggers predictions or reports model insights (Phase 5)
- Vision Agent: analyzes images/PDFs (Phase 6)
- General Agent: handles general questions that don't need specialized tools
"""
