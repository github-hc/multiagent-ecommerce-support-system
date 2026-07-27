import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastmcp import FastMCP
from app.config import settings
from app.logger import logger

mcp = FastMCP("Ecommerce Support Tools")
logger.info("Initializing FastMCP Ecommerce Support Tools server...")


@mcp.tool()
async def get_customer_profile(customer_id: str) -> dict:
    """Look up a customer's profile by their ID."""
    logger.info(f"[Tool] get_customer_profile invoked | customer_id: {customer_id}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}")
            if resp.status_code == 404:
                logger.warning(f"[Tool] get_customer_profile | Customer not found: {customer_id}")
                return {"error": "customer not found"}
            resp.raise_for_status()
            logger.info(f"[Tool] get_customer_profile | Success for customer_id: {customer_id}")
            return resp.json()
    except Exception as e:
        logger.error(f"[Tool] get_customer_profile | Error querying backend: {e}", exc_info=True)
        raise e


@mcp.tool()
async def get_order_details(order_id: str) -> dict:
    """Look up an order's details by its ID."""
    logger.info(f"[Tool] get_order_details invoked | order_id: {order_id}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.backend_base_url}/internal/orders/{order_id}")
            if resp.status_code == 404:
                logger.warning(f"[Tool] get_order_details | Order not found: {order_id}")
                return {"error": "order not found"}
            resp.raise_for_status()
            logger.info(f"[Tool] get_order_details | Success for order_id: {order_id}")
            return resp.json()
    except Exception as e:
        logger.error(f"[Tool] get_order_details | Error querying backend: {e}", exc_info=True)
        raise e


@mcp.tool()
async def get_customer_order_history(customer_id: str) -> list[dict]:
    """List all past orders for a customer."""
    logger.info(f"[Tool] get_customer_order_history invoked | customer_id: {customer_id}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}/orders")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[Tool] get_customer_order_history | Retrieved {len(data)} orders for customer_id: {customer_id}")
            return data
    except Exception as e:
        logger.error(f"[Tool] get_customer_order_history | Error querying backend: {e}", exc_info=True)
        raise e


@mcp.tool()
async def get_past_tickets(customer_id: str) -> list[dict]:
    """List past support tickets for a customer."""
    logger.info(f"[Tool] get_past_tickets invoked | customer_id: {customer_id}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}/tickets")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[Tool] get_past_tickets | Retrieved {len(data)} tickets for customer_id: {customer_id}")
            return data
    except Exception as e:
        logger.error(f"[Tool] get_past_tickets | Error querying backend: {e}", exc_info=True)
        raise e


if __name__ == "__main__":
    logger.info("Starting FastMCP Ecommerce Support Tools runner...")
    mcp.run()