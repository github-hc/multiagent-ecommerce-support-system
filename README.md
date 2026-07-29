# AI Ops Command Center — Multi-Agent Ecommerce Support System

Welcome to the **AI Ops Command Center**, a customer support ticket processing system. The core design is a collaborative multi-agent relay orchestrated using LangGraph, interacting with a secure MCP (Model Context Protocol) tool server, and audited live on an operational dashboard.

---

## How It Works

Imagine a customer support team where instead of one person handling everything, you have a **relay team of specialized AI agents** passing a ticket along, step-by-step. Each agent is a specialist focused on doing one job perfectly:

```mermaid
graph LR
    Triage["🔍 Triage Agent<br><i>(Classifies issue & urgency)</i>"] --> Research["🗄️ Research Agent<br><i>(Gathers context & policies)</i>"]
    Research --> Resolution["✍️ Resolution Agent<br><i>(Drafts reply & requests refund)</i>"]
    Resolution --> QA["✅ QA Agent<br><i>(Reviews & audits reply)</i>"]
    QA -->|"Refund case"| Human["🧑‍💼 Human Approval<br><i>(Manager reviews & decides)</i>"]
    Human --> Finalize["📬 Finalize Agent<br><i>(Saves reply & marks resolved)</i>"]
    QA -->|"Non-refund / approved"| Finalize
```

### Meet the AI Agents:

1. 🔍 **The Triage Agent (The Gatekeeper)**
   Looks at the incoming ticket, classifies it (e.g., as a refund request, bug report, or complaint), and determines how urgently it needs to be handled.
   * **Under the hood**: It parses raw ticket text using a local LLM (`llama3.1:8b`), outputs a structured category and priority, and patches the database classification via the MCP server.

2. 🗄️ **The Research Agent (The Fact-Finder)**
   Searches the company's internal knowledge base for relevant policy articles (like returns or shipping FAQs), looks up the customer's profile, and fetches their purchase history.
   * **Under the hood**: It generates text embeddings using `nomic-embed-text` and performs a pgvector similarity search on knowledge base documents, querying customer SQL records through MCP lookup tools.

3. ✍️ **The Resolution Agent (The Writer)**
   Takes the customer history and relevant policies gathered by the Research Agent to write a personalized, empathetic draft reply. If the policies show the request is eligible for a refund, it submits a request.
   * **Under the hood**: Prompts the LLM with customer data and policy context to produce a JSON response. If eligible, it calls the `create_refund_request` MCP tool to queue a database refund.

4. ✅ **The QA Agent (The Auditor)**
   Reviews the draft reply to ensure it is polite, clear, does not contradict policies, and does not make unauthorized promises. If not approved, it sends it back to the Resolution Agent with feedback (escalating after 2 attempts).
   * **Under the hood**: Prompts the LLM with the ticket, context, and draft response, parses its JSON score, updates the iteration counters, and logs the review trace via the MCP server.

5. 🧑‍💼 **The Human Approval Agent (The Manager)**
   Acts as a mandatory checkpoint for any ticket that requires a refund. The AI never issues refunds autonomously — the graph pauses here and waits for a human manager to approve or reject the action before continuing.
   * **Under the hood**: Uses LangGraph's `interrupt_before` mechanism to pause graph execution and persist state to PostgreSQL. A REST endpoint (`POST /tickets/{id}/resume`) accepts the human decision and resumes the graph. In MVP mode, approval is auto-simulated for faster local development.

6. 📬 **The Finalize Agent (The Closer)**
   Wraps up the ticket after all checks pass: saves the approved reply as a ticket message, marks the ticket status as `resolved`, and logs the final audit trace.
   * **Under the hood**: Calls `create_ticket_message`, `update_ticket_status`, and `create_trace` MCP tools to commit the final state to the database.

## System Architecture

The interaction flow between the components:

```mermaid
graph TD
    User([Customer Ticket]) -->|Submit Ticket| API[FastAPI Backend]
    API -->|Persist state| DB[(PostgreSQL + pgvector)]
    
    %% Agent Orchestrator
    subgraph AgentLoop ["Agent Loop (LangGraph)"]
        State([TicketState]) --> Triage[Triage Agent]
        Triage --> Research[Research Agent]
        Research --> Resolution[Resolution Agent]
        Resolution --> QA{QA Agent}
        
        QA -- "Approved + No Refund" --> Finalize[Finalize Agent]
        QA -->|"Rejected / Retry < 2"| Resolution
        QA -->|"Rejected / Retry >= 2"| Finalize
        QA -- "Approved + Refund" --> Human{Human Approval}
        Human -- "Approved" --> Finalize
        Human -- "Rejected" --> Resolution
        Finalize --> End([END])
    end
    
    API -->|Invoke Graph| State
    
    %% MCP server
    subgraph MCPServer ["MCP Server (Tools)"]
        KB[Search Knowledge Base]
        Profile[Get Customer Profile]
        Orders[Get Order Details]
        Refund[Request Refund]
        Ticket[Update Ticket Status]
        Msg[Create Ticket Message]
        Trace[Create Trace]
    end
    
    AgentLoop -->|"Call Tool (HTTP REST /call_tool)"| MCPServer
    MCPServer -->|HTTP Internal API| API
    
    %% Dashboard
    subgraph StreamlitDashboard ["Streamlit Dashboard"]
        Feed[Ticket Feed]
        Detail[Live Traces & Tool Calls]
        Queue[Approval Queue]
    end
    
    StreamlitDashboard -->|Query Traces & Approvals| API
    StreamlitDashboard -->|POST Approve / Reject| API
    API -.->|Interrupt State Checkpoints| DB
```

---

## Repository Structure

The codebase is organized into isolated, decoupled components:

- **[backend/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/)**: Core FastAPI web service and database schema definitions, including Alembic migrations and database seeding scripts.
- **[mcp_server/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/)**: A FastMCP server exposing database interactions as clean tools for the LLM agents.
- **[agents/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/agents/)**: LangGraph definition orchestrating the full agent pipeline — Triage → Research → Resolution → QA → Human Approval → Finalize.
- **dashboard/**: *(Planned)* Streamlit user interface visualizing live ticket feeds and handling human-in-the-loop approvals.

---

## Getting Started

You can run the entire stack (Database, Backend API, and MCP Server) together in a single command using Docker Compose, or run components individually for development.

### Method 1: Running with Docker Compose (Recommended)

1. Ensure **Ollama** is running locally on your host machine with the required models:
   ```bash
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text
   ```

2. Spin up the entire stack from the root directory:
   ```bash
   docker compose up --build
   ```
   *This automatically builds the backend and MCP server containers, launches a PostgreSQL container with `pgvector`, executes database migrations (`alembic upgrade head`), and exposes the services:*
   - **Backend API**: `http://localhost:8000`
   - **MCP Server**: `http://localhost:8001`

3. Seed the database (runs on host machine; requires backend virtual environment dependencies installed):
   ```bash
   cd backend
   source venv/bin/activate
   python -m seed.generate_data
   python -m seed.generate_embeddings
   ```

4. Start the Agents Service (runs on host machine; handles ticket graph execution):
   ```bash
   cd agents
   source venv/bin/activate
   uvicorn app.main:app --port 8002
   ```
   - **Agents Service**: `http://localhost:8002`

---

### Method 2: Manual Local Setup (Individual Components)

If you are modifying code and want hot-reloading for local development, refer to individual README guides:

1. Setup the Database and REST API: **[Backend README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/README.md)**
2. Setup and run the MCP tools layer: **[MCP Server README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/README.md)**
3. Setup and run the LangGraph workspace: **[Agents README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/agents/README.md)**

---

## Human-in-the-Loop Flow

When a refund is approved by the QA Agent, the workflow pauses at the **Human Approval** node. Here is how the two modes work:

### MVP Mode (default — fast local development)
The `MVP_AUTO_APPROVE = True` flag in [`human_approval.py`](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/agents/app/graph/nodes/human_approval.py) causes the node to auto-approve and the graph runs to `END` in a single `ainvoke()` call. No pause, no resume API call needed.

### Production Mode (real human-in-the-loop)
To enable real human approval:
1. Set `MVP_AUTO_APPROVE = False` in `human_approval.py`
2. Uncomment `interrupt_before=["human_approval"]` in `graph.py`

The graph will then **pause** after QA approval and return `{"status": "paused"}` from the `/run` endpoint. A human manager reviews and submits a decision:

```bash
# Approve the refund
curl -X POST http://localhost:8002/tickets/{ticket_id}/resume \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Reject the refund with a reason
curl -X POST http://localhost:8002/tickets/{ticket_id}/resume \
  -H "Content-Type: application/json" \
  -d '{"approved": false, "note": "Order is outside return window"}'
```

The graph then resumes from the `human_approval` node and continues to `finalize`.

---

## Observability & Logging Dashboard

We run a containerized observability stack consisting of **Grafana Loki** (log aggregator), **Promtail** (log shipper), and **Grafana** (dashboard UI) alongside the application containers.

To view the logs from all major execution steps:

1. Open **Grafana** in your browser: **[http://localhost:3000](http://localhost:3000)**
2. Log in using default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
   - *If prompted to change your password on first login, click the "Skip" button.*
3. Navigate to the **Explore** page by clicking the compass icon in the left-hand sidebar (or go directly to **[http://localhost:3000/explore](http://localhost:3000/explore)**).
4. Ensure **Loki** is selected in the data source dropdown at the top-left.
5. In the query text box (Code tab) or label browser, query the logs using:
   ```text
   {job="support-logs"}
   ```
6. Set the **Time Range Picker** (clock icon in the top-right, next to the run button) to **Last 1 hour** or **Last 3 hours** to make sure it includes the time you executed the ticket tests.
7. Click the blue **Run query** button in the top-right to display the logs.