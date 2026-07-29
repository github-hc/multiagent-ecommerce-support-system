import asyncio
import httpx
import logging
from app.config import settings
import app.logger

logger = logging.getLogger("test-runner")

SAMPLE_TICKET = {
    "channel": "email",
    "subject": "Refund for damaged item",
    "body": "The headphones I received were cracked. I'd like a refund please.",
}


async def get_sample_customer_with_order() -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/customers", params={"limit": 50})
        resp.raise_for_status()
        customers = resp.json()
        if not customers:
            raise RuntimeError("No customers found - did you run the seed script?")
        
        for customer in customers:
            cust_id = customer["id"]
            orders_resp = await client.get(f"{settings.backend_base_url}/internal/customers/{cust_id}/orders", timeout=30.0)
            orders_resp.raise_for_status()
            orders = orders_resp.json()
            if orders:
                return cust_id, orders[0]["id"]
                
        raise RuntimeError("No customers with orders found - did you run the seed script?")


async def create_ticket(customer_id: str, order_id: str = None) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {"customer_id": customer_id, **SAMPLE_TICKET}
        if order_id:
            payload["order_id"] = order_id
        resp = await client.post(
            f"{settings.backend_base_url}/internal/tickets",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["ticket_id"]


async def main():
    logger.info("Fetching a sample customer with orders...")
    customer_id, order_id = await get_sample_customer_with_order()
    logger.info(f"Using customer_id: {customer_id} | order_id: {order_id}")

    logger.info("Creating a test ticket...")
    ticket_id = await create_ticket(customer_id, order_id)
    logger.info(f"Created ticket_id: {ticket_id}")

    logger.info("Running the graph via Agents Service API...")
    
    # 1800s timeout to support slow local LLM embedding/chat operations
    async with httpx.AsyncClient(timeout=1800.0) as client:
        resp = await client.post(f"http://localhost:8002/tickets/{ticket_id}/run")
        resp.raise_for_status()
        run_result = resp.json()
        logger.info(f"Initial run status: {run_result.get('status')}")
        logger.info(f"Initial run output: {run_result}")

        # If the run was paused (which it should be, due to a refund request being raised),
        # simulate human review and resume it.
        if run_result.get("status") == "paused":
            logger.info("Graph paused successfully at Human-in-the-Loop node!")
            logger.info(f"Interrupt context: {run_result.get('interrupt')}")
            
            logger.info("Simulating human manager APPROVAL (sending resume with approved=True)...")
            resume_resp = await client.post(
                f"http://localhost:8002/tickets/{ticket_id}/resume",
                json={"approved": True}
            )
            resume_resp.raise_for_status()
            final_result = resume_resp.json()
            logger.info("Final completed state after resume:")
            logger.info(final_result)
        else:
            logger.info("Run finished directly without human interruption.")


if __name__ == "__main__":
    asyncio.run(main())