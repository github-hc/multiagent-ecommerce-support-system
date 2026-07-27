import json
import ollama
import httpx
import logging
from app.config import settings
from app.graph.state import TicketState
import app.logger

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
        parsed = json.loads(raw)
        category = parsed.get("category", "other")
        priority = parsed.get("priority", "medium")
        logger.info(f"[Triage Node] Parsed classification | category: {category} | priority: {priority}")
    except json.JSONDecodeError:
        logger.error("[Triage Node] JSON decode error parsing LLM response. Falling back to other/medium.", exc_info=True)
        category, priority = "other", "medium"

    new_state = {**state, "category": category, "priority": priority}

    # Persist classification to backend
    try:
        logger.info(f"[Triage Node] Patching classification to backend...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            patch_resp = await client.patch(
                f"{settings.backend_base_url}/internal/tickets/{ticket_id}/classification",
                json={"category": category, "priority": priority},
            )
            patch_resp.raise_for_status()
            logger.info("[Triage Node] Patch classification successful.")
            
            logger.info(f"[Triage Node] Logging execution trace to backend...")
            trace_resp = await client.post(
                f"{settings.backend_base_url}/internal/traces",
                json={
                    "ticket_id": ticket_id,
                    "agent_name": "triage_agent",
                    "step_number": 1,
                    "input_state": {"subject": state.get("subject"), "body": state["body"]},
                    "output_state": {"category": category, "priority": priority},
                    "reasoning_summary": f"Classified as {category}/{priority}",
                },
            )
            trace_resp.raise_for_status()
            logger.info("[Triage Node] Execution trace logging successful.")
    except Exception as e:
        logger.error(f"[Triage Node] Error communicating with backend: {e}", exc_info=True)
        # Note: we do not raise to prevent crashing the agent run, or we can raise depending on requirements.
        # Here we follow existing behavior.

    return new_state