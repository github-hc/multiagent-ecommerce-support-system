import logging
from app.graph.state import TicketState
import app.logger

logger = logging.getLogger("human-agent")

# MVP MODE: Human approval is simulated automatically.
# In a production system this node would pause via interrupt_before and
# wait for a real human decision delivered through the /tickets/{id}/resume endpoint.
# For local development we skip the blocking interrupt and auto-approve so the
# graph completes in a single ainvoke() call without extra memory/DB overhead.

MVP_AUTO_APPROVE = True  # flip to False to re-enable real human-in-the-loop


async def human_approval_node(state: TicketState) -> TicketState:
    ticket_id = state["ticket_id"]

    if MVP_AUTO_APPROVE:
        logger.info(
            f"[Human Approval Node] MVP mode — auto-approving ticket_id: {ticket_id}. "
            "Set MVP_AUTO_APPROVE=False in human_approval.py to enable real human review."
        )
        return {
            **state,
            "qa_approved": True,
            "requires_human_approval": False,
        }

    # --- Real human-in-the-loop path (used when interrupt_before is active) ---
    approved = state.get("qa_approved")
    if approved:
        logger.info(
            f"[Human Approval Node] Refund APPROVED by human for ticket_id: {ticket_id}"
        )
    else:
        note = state.get("qa_feedback") or "Human rejected the refund"
        logger.warning(
            f"[Human Approval Node] Refund REJECTED by human for ticket_id: {ticket_id}. "
            f"Reason: {note}"
        )
    return state
