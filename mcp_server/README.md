# MCP Server — Ecommerce Support Tools

This is the Model Context Protocol (MCP) server for the Ecommerce Support System. Built using Python's [FastMCP](https://github.com/jlowin/fastmcp) SDK, it exposes a secure set of actions (a "toolbox") that AI agents can use to fetch customers, orders, and ticket history from the backend. 

By separating database operations into an MCP server, the agents are decoupled from the physical database schema and interact solely with a restricted set of validated interfaces.

## Current Implementation Status

Currently, the MCP server is in a **partially completed state (Step 2)**:
- **Completed**: Read-only profile and history lookup tools.
- **Pending**: Knowledge base vector search, refund creation, ticket updates, and escalation tools.

---

## Tool API Reference

The server exposes tools defined in [server.py](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/app/server.py):

### 1. Active Tools (Lookup & Context)

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

---

### 2. Planned Tools (For future steps)

- **Search Knowledge Base**: Search articles in `kb_docs` using vector/semantic search.
- **Request Refund**: Creates a pending refund in the database (never auto-approves; triggers human validation).
- **Update Ticket Status**: Alters state of ticket in database.
- **Escalate Ticket**: Routes ticket escalation to a human agent.

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

Start the server standalone (transports via standard input/output):

```bash
python -m app.server
```

To test or inspect tools interactively, you can run the server via the MCP Inspector (if installed globally):

```bash
npx @modelcontextprotocol/inspector python -m app.server
```
