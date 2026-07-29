from langgraph.graph import StateGraph, END
from app.config import settings
from app.graph.state import TicketState
from app.graph.nodes.triage import triage_node
from app.graph.nodes.research import research_node
from app.graph.nodes.resolution import resolution_node
from app.graph.nodes.qa import qa_node
from app.graph.nodes.human_approval import human_approval_node
from app.graph.nodes.finalize import finalize_node

MAX_QA_ITERATIONS = 2


def route_after_qa(state: TicketState) -> str:
    if state["qa_approved"]:
        if state.get("requires_human_approval"):
            return "human_approval"
        return "finalize"

    if state.get("iteration_count", 0) >= MAX_QA_ITERATIONS:
        return "finalize"

    return "resolution"


def route_after_human_approval(state: TicketState) -> str:
    if state["qa_approved"]:
        return "finalize"
    if state.get("iteration_count", 0) >= MAX_QA_ITERATIONS:
        return "finalize"
    return "resolution"


def build_graph(checkpointer):
    graph = StateGraph(TicketState)
    graph.add_node("triage", triage_node)
    graph.add_node("research", research_node)
    graph.add_node("resolution", resolution_node)
    graph.add_node("qa", qa_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "research")
    graph.add_edge("research", "resolution")
    graph.add_edge("resolution", "qa")

    graph.add_conditional_edges("qa", route_after_qa, {
        "resolution": "resolution",
        "human_approval": "human_approval",
        "finalize": "finalize",
    })
    graph.add_conditional_edges("human_approval", route_after_human_approval, {
        "resolution": "resolution",
        "finalize": "finalize",
    })

    graph.add_edge("finalize", END)

    # MVP: interrupt_before disabled — graph runs to completion in one ainvoke().
    # Re-enable with interrupt_before=["human_approval"] when MVP_AUTO_APPROVE=False.
    return graph.compile(checkpointer=checkpointer)

