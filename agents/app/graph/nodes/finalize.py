import logging
from app.config import settings
from app.graph.state import TicketState
from app.mcp_client import call_tool
import app.logger

logger = logging.getLogger("finalize-agent")


async def finalize_node(state: TicketState) -> TicketState:
    ticket_id = state["ticket_id"]
    logger.info(f"[Finalize Node] Entering finalize node for ticket_id: {ticket_id}")

    try:
        # 1. Save the final reply as a ticket message using MCP tool
        logger.info("[Finalize Node] Saving draft response as ticket message via MCP...")
        await call_tool(
            "create_ticket_message",
            {
                "ticket_id": ticket_id,
                "sender_type": "agent",
                "content": state["draft_response"]
            }
        )
        logger.info("[Finalize Node] Ticket message saved successfully.")

        # 2. Mark the ticket resolved using MCP tool
        logger.info("[Finalize Node] Marking ticket status as resolved via MCP...")
        await call_tool(
            "update_ticket_status",
            {
                "ticket_id": ticket_id,
                "status": "resolved"
            }
        )
        logger.info("[Finalize Node] Ticket status set to resolved.")

        # 3. Log step 5 trace using MCP tool
        logger.info("[Finalize Node] Logging final trace via MCP...")
        await call_tool(
            "create_trace",
            {
                "ticket_id": ticket_id,
                "agent_name": "finalize",
                "step_number": 5,
                "input_state": {"draft_response": state["draft_response"]},
                "output_state": {"status": "resolved"},
                "reasoning_summary": "Ticket finalized and marked resolved",
            }
        )
        logger.info("[Finalize Node] Final execution trace logged successfully.")

    except Exception as e:
        logger.error(f"[Finalize Node] Error during finalization steps: {e}", exc_info=True)
        raise e

    return state
