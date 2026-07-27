import asyncio
import sys
import httpx
from app.config import settings
from app.graph.graph import compiled_graph


async def run_for_ticket(ticket_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/tickets/{ticket_id}")
        resp.raise_for_status()
        ticket = resp.json()

    initial_state = {
        "ticket_id": ticket["id"],
        "customer_id": ticket["customer_id"],
        "order_id": ticket["order_id"],
        "subject": ticket["subject"],
        "body": ticket["body"],
        "category": None,
        "priority": None,
        "kb_results": [],
        "draft_response": None,
        "qa_approved": False,
        "iteration_count": 0,
        "requires_human_approval": False,
    }

    result = await compiled_graph.ainvoke(initial_state)
    print("Final state:", result)


if __name__ == "__main__":
    ticket_id = sys.argv[1]
    asyncio.run(run_for_ticket(ticket_id))