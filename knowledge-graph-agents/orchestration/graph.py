"""LangGraph StateGraph definition for the multi-agent Knowledge Graph system."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.analyst import analyst_node
from agents.ingestion import ingestion_node
from agents.kgc import kgc_node
from agents.monitor import monitor_node
from agents.orchestrator import orchestrator_node
from agents.synthesis import synthesis_node
from agents.validator import validator_node
from orchestration.state import AgentState, Intent


def route_by_intent(state: AgentState) -> str:
    """Return the name of the next node based on the classified intent.

    This function is used as the conditional edge from the orchestrator node.
    """
    intent = state.get("intent")
    routing: dict[str, str] = {
        Intent.INGEST.value: "ingestion",
        Intent.QUERY.value: "analyst",
        Intent.ANALYZE.value: "analyst",
        Intent.SYNTHESIZE.value: "synthesis",
        Intent.VALIDATE.value: "validator",
        Intent.KGC.value: "kgc",
        Intent.MONITOR.value: "monitor",
        Intent.HEALTH.value: "monitor",
    }
    return routing.get(intent or "", "analyst")


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph multi-agent workflow.

    Returns:
        A compiled ``StateGraph`` ready to invoke.
    """
    workflow = StateGraph(AgentState)

    # Register all agent nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("kgc", kgc_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("monitor", monitor_node)

    # Entry point
    workflow.set_entry_point("orchestrator")

    # Orchestrator conditionally routes to the right specialist
    workflow.add_conditional_edges(
        "orchestrator",
        route_by_intent,
        {
            "ingestion": "ingestion",
            "analyst": "analyst",
            "validator": "validator",
            "kgc": "kgc",
            "synthesis": "synthesis",
            "monitor": "monitor",
        },
    )

    # After ingestion always run validator (post-ingest quality check)
    workflow.add_edge("ingestion", "validator")
    workflow.add_edge("validator", END)

    # KGC flows through synthesis for the gap-analysis report
    workflow.add_edge("kgc", "synthesis")
    workflow.add_edge("synthesis", END)

    # Terminal nodes
    workflow.add_edge("analyst", END)
    workflow.add_edge("monitor", END)

    return workflow.compile()


# Module-level compiled graph (import and invoke directly)
agent_graph = build_graph()
