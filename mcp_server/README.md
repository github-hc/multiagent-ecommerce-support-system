# MCP Server — Ecommerce Support Tools

This is the Model Context Protocol (MCP) server for the Ecommerce Support System. Built using Python's [FastMCP](https://github.com/jlowin/fastmcp) SDK, it exposes a secure set of actions (a "toolbox") that AI agents use to perform operations (read/write/search) via the backend.

By separating backend operations into an MCP server, the agents are decoupled from the physical database schema and interact solely with a restricted set of validated interfaces.

Additionally, this server runs a standard FastAPI wrapper providing a direct **HTTP REST Gateway** (`/call_tool`) to allow agent runtimes without the full MCP client SDK to easily invoke tools over HTTP.

---

## Tool API Reference

The server exposes tools defined in [server.py](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/app/server.py):

### 1. Context Lookup & Operations

#### `get_customer_profile`
- **Arguments**: `customer_id: str`
- **Function**: Queries backend `GET /internal/customers/{customer_id}` and returns the customer's tier, signup date, email, and name.

#### `get_order_details`
- **Arguments**: `order_id: str`
- **Function**: Queries backend `GET /internal/orders/{order_id}` and returns order details (amount, status, items bought, date).

#### `get_customer_order_history`
- **Arguments**: `customer_id: str`
- **Function**: Queries backend `GET /internal/customers/{customer_id}/orders` and returns a list of all historical orders.

#### `get_past_tickets`
- **Arguments**: `customer_id: str`
- **Function**: Queries backend `GET /internal/customers/{customer_id}/tickets` and returns past support ticket logs.

### 2. Decision Support & State Actions

#### `search_knowledge_base`
- **Arguments**: `query: str`, `top_k: int = 3`
- **Function**: Queries backend `GET /internal/kb/search` to generate embeddings and run a pgvector similarity search on knowledge base docs.

#### `classify_ticket`
- **Arguments**: `ticket_id: str`, `category: str`, `priority: str`
- **Function**: Patches the ticket's category and priority to backend `PATCH /internal/tickets/{ticket_id}/classification`.

#### `create_trace`
- **Arguments**: `ticket_id: str`, `agent_name: str`, `step_number: int`, `input_state: dict`, `output_state: dict`, `reasoning_summary: str`
- **Function**: Logs an agent execution step audit log to backend `POST /internal/traces`.

---

## Setup & Running Instructions

### 1. Installation

Create a virtual environment inside the `mcp_server/` directory and install the requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Copy the environment example file:

```bash
cp .env.example .env
```

Configured variables:
- `BACKEND_BASE_URL`: Endpoint of the FastAPI service (defaults to `http://localhost:8000`).

### 3. Run the Server

#### Option A: Running as an HTTP / SSE Server (Recommended)
This runs the FastAPI app exposing the custom REST endpoint `/call_tool` alongside the standard `/mcp/sse` MCP transport:

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8001
```

#### Option B: Standalone stdio Runner
Runs the server utilizing standard input/output transport:

```bash
python -m app.server
```

---

## HTTP REST Gateway Usage

To consume the tools via simple HTTP without the full MCP client stack, send a `POST` request to `http://localhost:8001/call_tool`:

**Example Payload:**
```json
{
  "name": "get_customer_profile",
  "arguments": {
    "customer_id": "063d7cc8-e449-4c4b-9ff4-d68a526e2cae"
  }
}
```

**Example Response:**
```json
{
  "status": "success",
  "result": {
    "id": "063d7cc8-e449-4c4b-9ff4-d68a526e2cae",
    "name": "Nicole Cox",
    "email": "nicole.cox@example.com",
    "tier": "gold"
  }
}
```
