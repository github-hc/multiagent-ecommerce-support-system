from langgraph.graph import StateGraph, END
from app.graph.state import TicketState
from app.graph.nodes.triage import triage_node
from app.graph.nodes.research import research_node

def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("triage", triage_node)
    graph.add_node("research", research_node)
    graph.set_entry_point("triage")
    graph.add_edge("triage", "research")
    graph.add_edge("research", END)
    return graph.compile()


compiled_graph = build_graph()