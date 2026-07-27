import httpx
import logging
from app.config import settings

logger = logging.getLogger("triage-agent")


async def call_tool(name: str, arguments: dict = None) -> any:
    """Call an MCP tool over the custom HTTP REST API gateway."""
    if arguments is None:
        arguments = {}

    url = f"{settings.mcp_server_url}/call_tool"
    logger.info(f"[MCP Client] Sending POST to {url} | calling tool: {name} with arguments: {arguments}")

    try:
        # 120s timeout to support high system load / slow DB operations under local LLM execution
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json={"name": name, "arguments": arguments})
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "error":
                logger.error(f"[MCP Client] Tool execution error from server: {data.get('message')}")
                raise RuntimeError(f"MCP Tool execution error: {data.get('message')}")

            logger.info(f"[MCP Client] Tool {name} execution succeeded")
            return data.get("result")
    except Exception as e:
        logger.error(f"[MCP Client] Connection or execution error calling tool {name}: {e}", exc_info=True)
        raise e
