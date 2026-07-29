import json
import ollama
import logging
from app.config import settings
from app.graph.state import TicketState
from app.mcp_client import call_tool
import app.logger
from app.utils import clean_and_parse_json

logger = logging.getLogger("triage-agent")

TRIAGE_PROMPT = """You are a support ticket triage agent for an e-commerce company.
Read the ticket and classify it. Respond with ONLY a JSON object, no other text.

Categories: billing, bug, how_to, refund, complaint, other
Priorities: low, medium, high, urgent

Ticket subject: {subject}
Ticket body: {body}

Respond exactly in this format:
{{"category": "...", "priority": "..."}}
"""


async def triage_node(state: TicketState) -> TicketState:
    ticket_id = state.get("ticket_id")
    logger.info(f"[Triage Node] Processing ticket_id: {ticket_id}")
    
    prompt = TRIAGE_PROMPT.format(subject=state.get("subject") or "", body=state["body"])
    logger.info(f"[Triage Node] Invoking local Ollama model: {settings.ollama_model}")

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response["message"]["content"].strip()
        logger.info(f"[Triage Node] Raw LLM Response: {raw}")
    except Exception as e:
        logger.error(f"[Triage Node] Failed to query Ollama: {e}", exc_info=True)
        raise e

    try:
        parsed = clean_and_parse_json(raw)
        category = parsed.get("category", "other")
        priority = parsed.get("priority", "medium")
        logger.info(f"[Triage Node] Parsed classification | category: {category} | priority: {priority}")
    except Exception:
        logger.error("[Triage Node] JSON decode error parsing LLM response. Falling back to other/medium.", exc_info=True)
        category, priority = "other", "medium"

    new_state = {**state, "category": category, "priority": priority}

    # Persist classification to backend via MCP
    try:
        logger.info(f"[Triage Node] Patching classification via MCP server...")
        await call_tool(
            "classify_ticket",
            {"ticket_id": ticket_id, "category": category, "priority": priority}
        )
        logger.info("[Triage Node] Patch classification successful via MCP.")
        
        logger.info(f"[Triage Node] Logging execution trace via MCP server...")
        await call_tool(
            "create_trace",
            {
                "ticket_id": ticket_id,
                "agent_name": "triage_agent",
                "step_number": 1,
                "input_state": {"subject": state.get("subject"), "body": state["body"]},
                "output_state": {"category": category, "priority": priority},
                "reasoning_summary": f"Classified as {category}/{priority}",
            }
        )
        logger.info("[Triage Node] Execution trace logging successful via MCP.")
    except Exception as e:
        logger.error(f"[Triage Node] Error communicating via MCP server: {e}", exc_info=True)

    return new_state