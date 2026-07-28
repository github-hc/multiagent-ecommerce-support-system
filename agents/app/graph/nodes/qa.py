import json
import ollama
import logging
from app.config import settings
from app.graph.state import TicketState
from app.mcp_client import call_tool
import app.logger

logger = logging.getLogger("qa-agent")

QA_PROMPT = """You are a QA reviewer checking a customer support reply before it is sent.

Customer's original message: {body}

Relevant knowledge base articles (the reply must not contradict these):
{kb_context}

Drafted reply to review:
{draft}

Check that the reply:
- Is polite and clear
- Does not contradict the knowledge base articles
- Does not make promises the company can't keep (e.g. guaranteeing a refund
  amount or timeline the KB articles don't support)

Respond with ONLY a JSON object in this exact format, no other text:
{{
  "approved": true or false,
  "feedback": "if rejected, a short specific reason; if approved, empty string"
}}
"""


def format_kb_context(kb_results: list) -> str:
    if not kb_results:
        return "No relevant articles found."
    return "\n\n".join(f"- {doc['title']}: {doc['content']}" for doc in kb_results)


async def qa_node(state: TicketState) -> TicketState:
    ticket_id = state.get("ticket_id")
    logger.info(f"[QA Node] Processing ticket_id: {ticket_id} | iteration: {state.get('iteration_count', 0)}")

    prompt = QA_PROMPT.format(
        body=state["body"],
        kb_context=format_kb_context(state.get("kb_results", [])),
        draft=state.get("draft_response", ""),
    )

    logger.info(f"[QA Node] Invoking local Ollama model: {settings.ollama_model}")
    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response["message"]["content"].strip()
        logger.info(f"[QA Node] Raw LLM Response: {raw}")
    except Exception as e:
        logger.error(f"[QA Node] Failed to query Ollama: {e}", exc_info=True)
        raise e

    try:
        parsed = json.loads(raw)
        approved = parsed.get("approved", False)
        feedback = parsed.get("feedback", "")
        logger.info(f"[QA Node] Parsed review | approved: {approved} | feedback: {feedback}")
    except json.JSONDecodeError:
        logger.error("[QA Node] JSON decode error parsing LLM response. Falling back to rejection.", exc_info=True)
        # if QA itself fails to respond cleanly, don't auto-approve - treat as rejected
        approved = False
        feedback = "QA agent response could not be parsed - treating as rejected for safety"

    new_iteration_count = state.get("iteration_count", 0)
    if not approved:
        new_iteration_count += 1

    new_state = {
        **state,
        "qa_approved": approved,
        "qa_feedback": feedback if not approved else None,
        "iteration_count": new_iteration_count,
    }

    # Log the trace via MCP
    logger.info("[QA Node] Logging execution trace via MCP server...")
    try:
        await call_tool(
            "create_trace",
            {
                "ticket_id": ticket_id,
                "agent_name": "qa_agent",
                "step_number": 4,
                "input_state": {
                    "draft_response": state.get("draft_response"),
                    "iteration_count": state.get("iteration_count", 0),
                },
                "output_state": {
                    "qa_approved": approved,
                    "qa_feedback": feedback,
                    "iteration_count": new_iteration_count,
                },
                "reasoning_summary": f"Review complete. Approved: {approved}. Feedback: {feedback}",
            }
        )
        logger.info("[QA Node] Execution trace logging successful via MCP.")
    except Exception as e:
        logger.error(f"[QA Node] Error logging trace: {e}", exc_info=True)

    return new_state