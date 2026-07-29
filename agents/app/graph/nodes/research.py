import logging
from app.config import settings
from app.graph.state import TicketState
from app.mcp_client import call_tool
import app.logger

logger = logging.getLogger("research-agent")


async def research_node(state: TicketState) -> TicketState:
    logger.info(f"[Research Node] Entering research node for customer_id: {state['customer_id']}")

    customer_profile = await call_tool("get_customer_profile", {"customer_id": state["customer_id"]})
    order_history = await call_tool("get_customer_order_history", {"customer_id": state["customer_id"]})
    past_tickets = await call_tool("get_past_tickets", {"customer_id": state["customer_id"]})

    # Use the ticket body itself as the KB search query
    kb_results = await call_tool(
        "search_knowledge_base",
        {"query": state["body"], "top_k": 3},
    )

    order_id = state.get("order_id")
    if not order_id and order_history:
        order_id = order_history[0]["id"]
        logger.info(f"[Research Node] Associated ticket with customer's most recent order: {order_id}")

    order_details = None
    if order_id:
        order_details = await call_tool("get_order_details", {"order_id": order_id})

    new_state = {
        **state,
        "order_id": order_id,
        "kb_results": kb_results,
    }

    # Log the trace via MCP
    logger.info("[Research Node] Logging execution trace via MCP server...")
    try:
        await call_tool(
            "create_trace",
            {
                "ticket_id": state["ticket_id"],
                "agent_name": "research_agent",
                "step_number": 2,
                "input_state": {"customer_id": state["customer_id"], "order_id": state.get("order_id")},
                "output_state": {
                    "customer_profile": customer_profile,
                    "order_history_count": len(order_history) if order_history else 0,
                    "past_tickets_count": len(past_tickets) if past_tickets else 0,
                    "order_details": order_details,
                    "kb_results_count": len(kb_results) if kb_results else 0,
                },
                "reasoning_summary": f"Gathered customer context and {len(kb_results) if kb_results else 0} relevant KB articles",
            }
        )
        logger.info("[Research Node] Execution trace logging successful via MCP.")
    except Exception as e:
        logger.error(f"[Research Node] Error logging trace: {e}", exc_info=True)

    return new_state