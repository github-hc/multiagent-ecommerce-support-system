import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastmcp import FastMCP
from app.config import settings

mcp = FastMCP("Ecommerce Support Tools")


@mcp.tool()
async def get_customer_profile(customer_id: str) -> dict:
    """Look up a customer's profile by their ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}")
        if resp.status_code == 404:
            return {"error": "customer not found"}
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_order_details(order_id: str) -> dict:
    """Look up an order's details by its ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/orders/{order_id}")
        if resp.status_code == 404:
            return {"error": "order not found"}
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_customer_order_history(customer_id: str) -> list[dict]:
    """List all past orders for a customer."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}/orders")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_past_tickets(customer_id: str) -> list[dict]:
    """List past support tickets for a customer."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}/tickets")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run()