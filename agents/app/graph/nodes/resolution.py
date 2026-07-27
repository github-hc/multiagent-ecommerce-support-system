import json
import ollama
import logging
from app.config import settings
from app.graph.state import TicketState
from app.mcp_client import call_tool
import app.logger

logger = logging.getLogger("resolution-agent")

RESOLUTION_PROMPT = """You are a customer support agent for an e-commerce company.
Write a helpful, empathetic reply to the customer's ticket, using the context below.

Ticket category: {category}
Ticket priority: {priority}
Customer message: {body}

Relevant knowledge base articles:
{kb_context}

Decide if this situation warrants a refund. Only recommend a refund if the
knowledge base context supports it (e.g. damaged item, policy allows it).

Respond with ONLY a JSON object in this exact format, no other text:
{{
  "reply": "the customer-facing reply text",
  "needs_refund": true or false,
  "refund_amount": a number or null,
  "refund_reason": "short reason" or null
}}
"""


def format_kb_context(kb_results: list) -> str:
    if not kb_results:
        return "No relevant articles found."
    return "\n\n".join(f"- {doc['title']}: {doc['content']}" for doc in kb_results)


async def resolution_node(state: TicketState) -> TicketState:
    ticket_id = state.get("ticket_id")
    logger.info(f"[Resolution Node] Processing ticket_id: {ticket_id}")

    prompt = RESOLUTION_PROMPT.format(
        category=state.get("category"),
        priority=state.get("priority"),
        body=state["body"],
        kb_context=format_kb_context(state.get("kb_results", [])),
    )

    # if QA rejected a previous draft, include that feedback
    if state.get("qa_feedback"):
        logger.info(f"[Resolution Node] Applying QA feedback from previous iteration: {state['qa_feedback']}")
        prompt += f"\n\nNote: a previous draft was rejected for this reason - fix it: {state['qa_feedback']}"

    logger.info(f"[Resolution Node] Invoking local Ollama model: {settings.ollama_model}")
    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response["message"]["content"].strip()
        logger.info(f"[Resolution Node] Raw LLM Response: {raw}")
    except Exception as e:
        logger.error(f"[Resolution Node] Failed to query Ollama: {e}", exc_info=True)
        raise e

    try:
        parsed = json.loads(raw)
        reply = parsed.get("reply", "")
        needs_refund = parsed.get("needs_refund", False)
        refund_amount = parsed.get("refund_amount")
        refund_reason = parsed.get("refund_reason")
        logger.info(f"[Resolution Node] Parsed draft response | needs_refund: {needs_refund} | amount: {refund_amount}")
    except json.JSONDecodeError:
        logger.error("[Resolution Node] JSON decode error parsing LLM response. Falling back to safe defaults.", exc_info=True)
        # safe fallback - never silently invent a refund on a parse failure
        reply = raw
        needs_refund = False
        refund_amount = None
        refund_reason = None

    refund_requested = False
    if needs_refund and state.get("order_id") and refund_amount:
        logger.info(f"[Resolution Node] Triggering refund request tool via MCP server...")
        try:
            await call_tool(
                "create_refund_request",
                {
                    "order_id": state["order_id"],
                    "ticket_id": state["ticket_id"],
                    "amount": refund_amount,
                    "reason": refund_reason or "Resolution agent determined refund was warranted",
                },
            )
            refund_requested = True
            logger.info("[Resolution Node] Refund request created successfully via MCP.")
        except Exception as e:
            logger.error(f"[Resolution Node] Error calling refund request tool: {e}", exc_info=True)

    new_state = {
        **state,
        "draft_response": reply,
        "requires_human_approval": refund_requested,
    }

    # Log the trace via MCP
    logger.info("[Resolution Node] Logging execution trace via MCP server...")
    try:
        await call_tool(
            "create_trace",
            {
                "ticket_id": ticket_id,
                "agent_name": "resolution_agent",
                "step_number": 3,
                "input_state": {"category": state.get("category"), "kb_results_count": len(state.get("kb_results", []))},
                "output_state": {"draft_response": reply, "refund_requested": refund_requested},
                "reasoning_summary": f"Drafted reply. Refund requested: {refund_requested}",
            }
        )
        logger.info("[Resolution Node] Execution trace logging successful via MCP.")
    except Exception as e:
        logger.error(f"[Resolution Node] Error logging trace: {e}", exc_info=True)

    return new_state