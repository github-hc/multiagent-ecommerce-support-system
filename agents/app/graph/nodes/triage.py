import json
import ollama
import httpx
from app.config import settings
from app.graph.state import TicketState

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
    prompt = TRIAGE_PROMPT.format(subject=state.get("subject") or "", body=state["body"])

    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response["message"]["content"].strip()

    try:
        parsed = json.loads(raw)
        category = parsed.get("category", "other")
        priority = parsed.get("priority", "medium")
    except json.JSONDecodeError:
        # SLMs sometimes wrap JSON in extra text - fall back safely instead of crashing the graph
        category, priority = "other", "medium"

    new_state = {**state, "category": category, "priority": priority}

    # persist classification to backend
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{settings.backend_base_url}/internal/tickets/{state['ticket_id']}/classification",
            json={"category": category, "priority": priority},
        )
        await client.post(
            f"{settings.backend_base_url}/internal/traces",
            json={
                "ticket_id": state["ticket_id"],
                "agent_name": "triage_agent",
                "step_number": 1,
                "input_state": {"subject": state.get("subject"), "body": state["body"]},
                "output_state": {"category": category, "priority": priority},
                "reasoning_summary": f"Classified as {category}/{priority}",
            },
        )

    return new_state