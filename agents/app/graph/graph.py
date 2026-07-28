from langgraph.graph import StateGraph, END
from app.graph.state import TicketState
from app.graph.nodes.triage import triage_node
from app.graph.nodes.research import research_node
from app.graph.nodes.resolution import resolution_node
from app.graph.nodes.qa import qa_node


MAX_QA_ITERATIONS = 2


def route_after_qa(state: TicketState) -> str:
    if state["qa_approved"]:
        if state.get("requires_human_approval"):
            return "end"
        return "end"

    if state.get("iteration_count", 0) >= MAX_QA_ITERATIONS:
        return "end"

    return "resolution"


def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("triage", triage_node)
    graph.add_node("research", research_node)
    graph.add_node("resolution", resolution_node)
    graph.add_node("qa", qa_node)
    graph.set_entry_point("triage")
    graph.add_edge("triage", "research")
    graph.add_edge("research", "resolution")
    graph.add_edge("resolution", "qa")
    graph.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "end": END,
            "resolution": "resolution",
        },
    )
    return graph.compile()


compiled_graph = build_graph()