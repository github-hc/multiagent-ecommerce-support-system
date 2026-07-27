import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastapi import FastAPI, Body, HTTPException
from fastmcp import FastMCP
from app.config import settings
from app.logger import logger

# Initialize FastMCP
mcp = FastMCP("Ecommerce Support Tools")
logger.info("Initializing FastMCP Ecommerce Support Tools server...")

# ----------------- MCP Tools Definitions -----------------

@mcp.tool()
async def get_customer_profile(customer_id: str) -> dict:
    """Look up a customer's profile by their ID."""
    logger.info(f"[Tool] get_customer_profile invoked | customer_id: {customer_id}")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
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
        async with httpx.AsyncClient(timeout=120.0) as client:
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
        async with httpx.AsyncClient(timeout=120.0) as client:
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{settings.backend_base_url}/internal/customers/{customer_id}/tickets")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[Tool] get_past_tickets | Retrieved {len(data)} tickets for customer_id: {customer_id}")
            return data
    except Exception as e:
        logger.error(f"[Tool] get_past_tickets | Error querying backend: {e}", exc_info=True)
        raise e


@mcp.tool()
async def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """Search the knowledge base for policies and articles by semantic query."""
    logger.info(f"[Tool] search_knowledge_base invoked | query: '{query}' | top_k: {top_k}")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(
                f"{settings.backend_base_url}/internal/kb/search",
                params={"query": query, "limit": top_k}
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[Tool] search_knowledge_base | Retrieved {len(data)} matching docs")
            return data
    except Exception as e:
        logger.error(f"[Tool] search_knowledge_base | Error: {e}", exc_info=True)
        raise e


@mcp.tool()
async def classify_ticket(ticket_id: str, category: str, priority: str) -> dict:
    """Update a support ticket's classification in the backend database."""
    logger.info(f"[Tool] classify_ticket invoked | ticket_id: {ticket_id} | category: {category} | priority: {priority}")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.patch(
                f"{settings.backend_base_url}/internal/tickets/{ticket_id}/classification",
                json={"category": category, "priority": priority}
            )
            resp.raise_for_status()
            logger.info(f"[Tool] classify_ticket | Classification update success for ticket_id: {ticket_id}")
            return resp.json()
    except Exception as e:
        logger.error(f"[Tool] classify_ticket | Error: {e}", exc_info=True)
        raise e


@mcp.tool()
async def create_trace(
    ticket_id: str,
    agent_name: str,
    step_number: int,
    input_state: dict,
    output_state: dict,
    reasoning_summary: str
) -> dict:
    """Log an agent trace entry in the backend database."""
    logger.info(f"[Tool] create_trace invoked | ticket_id: {ticket_id} | agent: {agent_name} | step: {step_number}")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.backend_base_url}/internal/traces",
                json={
                    "ticket_id": ticket_id,
                    "agent_name": agent_name,
                    "step_number": step_number,
                    "input_state": input_state,
                    "output_state": output_state,
                    "reasoning_summary": reasoning_summary
                }
            )
            resp.raise_for_status()
            logger.info(f"[Tool] create_trace | Trace log success for ticket_id: {ticket_id}")
            return resp.json()
    except Exception as e:
        logger.error(f"[Tool] create_trace | Error: {e}", exc_info=True)
        raise e


# ----------------- FastAPI Web Server Wrapper -----------------

mcp_app = mcp.http_app()
app = FastAPI(title="MCP HTTP Gateway", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)

# Map names to functions for the simple REST endpoint
tool_map = {
    "get_customer_profile": get_customer_profile,
    "get_order_details": get_order_details,
    "get_customer_order_history": get_customer_order_history,
    "get_past_tickets": get_past_tickets,
    "search_knowledge_base": search_knowledge_base,
    "classify_ticket": classify_ticket,
    "create_trace": create_trace,
}


@app.post("/call_tool")
async def call_tool_endpoint(name: str = Body(...), arguments: dict = Body(default={})):
    logger.info(f"[REST API] Calling tool {name} with arguments: {arguments}")
    if name not in tool_map:
        logger.error(f"[REST API] Tool {name} not found")
        raise HTTPException(status_code=404, detail=f"Tool {name} not found")
    
    try:
        result = await tool_map[name](**arguments)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"[REST API] Error executing tool {name}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    logger.info("Starting FastMCP Ecommerce Support Tools runner in standard mode...")
    mcp.run()