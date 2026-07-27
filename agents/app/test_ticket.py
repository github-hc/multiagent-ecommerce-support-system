import asyncio
import httpx
from app.config import settings
from app.graph.graph import compiled_graph

SAMPLE_TICKET = {
    "channel": "email",
    "subject": "Refund for damaged item",
    "body": "The headphones I received were cracked. I'd like a refund please.",
}


async def get_sample_customer_id() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/customers", params={"limit": 1})
        resp.raise_for_status()
        customers = resp.json()
        if not customers:
            raise RuntimeError("No customers found - did you run the seed script?")
        return customers[0]["id"]


async def create_ticket(customer_id: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.backend_base_url}/internal/tickets",
            json={"customer_id": customer_id, **SAMPLE_TICKET},
        )
        resp.raise_for_status()
        return resp.json()["ticket_id"]


async def get_ticket(ticket_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/tickets/{ticket_id}")
        resp.raise_for_status()
        return resp.json()


async def main():
    print("Fetching a sample customer...")
    customer_id = await get_sample_customer_id()
    print(f"Using customer_id: {customer_id}")

    print("Creating a test ticket...")
    ticket_id = await create_ticket(customer_id)
    print(f"Created ticket_id: {ticket_id}")

    ticket = await get_ticket(ticket_id)

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

    print("Running the graph...")
    result = await compiled_graph.ainvoke(initial_state)
    print("\nFinal state:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())