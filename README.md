# AI Ops Command Center — Multi-Agent Ecommerce Support System

Welcome to the **AI Ops Command Center**, a customer support ticket processing system. The core design is a collaborative multi-agent relay orchestrated using LangGraph, interacting with a secure MCP (Model Context Protocol) tool server, and audited live on an operational dashboard.

---

## The Workflow in a Nutshell

When a customer support ticket is received:
1. **Triage Agent** classifies the ticket by category and priority.
2. **Research Agent** calls MCP tools to collect customer facts, order history, and policy search hits.
3. **Resolution Agent** drafts a tailored resolution or requests a refund if eligible.
4. **QA Agent** reviews the draft, either approving it or routing it back for revision (escalating to humans after 2 attempts).
5. **Human-in-the-Loop Interruption** pauses execution for operations requiring authorization (e.g. refunds), waiting on human approval before concluding.
6. **Command Center Dashboard** visualizes the traces, tool calls, and approval queues live.

---

## System Architecture

The interaction flow between the components:

```mermaid
graph TD
    User([Customer Ticket]) -->|Submit Ticket| API[FastAPI Backend]
    API -->|Persist state| DB[(PostgreSQL + pgvector)]
    
    %% Agent Orchestrator
    subgraph Agent Loop (LangGraph)
        State([TicketState]) --> Triage[Triage Agent]
        Triage --> Research[Research Agent]
        Research --> Resolution[Resolution Agent]
        Resolution --> QA{QA Agent}
        
        QA -- Approved --> EndState([Resolved State])
        QA -- Rejected / Retry < 2 --> Resolution
        QA -- Rejected / Retry >= 2 --> Escalate([Escalate to Human])
    end
    
    API -->|Invoke Graph| State
    
    %% MCP server
    subgraph MCP Server (Tools)
        KB[Search Knowledge Base]
        Profile[Get Customer Profile]
        Orders[Get Order Details]
        Refund[Request Refund]
    end
    
    Research & Resolution -->|Query / Action| MCP Server
    MCP Server -->|HTTP Internal API| API
    
    %% Dashboard
    subgraph Streamlit Dashboard
        Feed[Ticket Feed]
        Detail[Live Traces & Tool Calls]
        Queue[Approval Queue]
    end
    
    Streamlit Dashboard -->|Query Traces & Approvals| API
    Streamlit Dashboard -->|POST Approve / Reject| API
    API -.->|Interrupt State Checkpoints| DB
```

---

## Repository Structure

The codebase is organized into isolated, decoupled components:

- **[backend/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/)**: Core FastAPI web service and database schema definitions, including Alembic migrations and database seeding scripts.
- **[mcp_server/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/)**: A FastMCP server exposing database interactions as clean tools for the LLM agents.
- **[agents/](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/agents/)**: LangGraph definition orchestrating agent node tasks (Triage, Research, Resolution, QA).
- **dashboard/**: *(Planned - Step 6)* Streamlit user interface visualizing live ticket feeds and handling human-in-the-loop approvals.

---

## Implementation Progress Checklist

This project is currently in the **Halfway Stage (Step 3 completed)**.

- [x] **Step 1: Set up the database**
  - PostgreSQL schema containing `customers`, `orders`, `tickets`, `agent_traces`, `tool_calls`, `refunds`, and `kb_docs` tables.
  - Alembic migration pipeline.
  - Fake data generator (Faker) and Knowledge Base embedding loader (pgvector + Ollama).
- [x] **Step 2: Build the MCP server (the "hands")**
  - FastMCP framework setup.
  - Database lookup tools for customer profiles, order details, and ticket histories.
  - [ ] *Pending*: Knowledge Base semantic search and refund/update/escalate tools.
- [x] **Step 3: Build one agent, end to end**
  - LangGraph environment setup.
  - Triage Agent node using local Ollama model (`llama3.1:8b`) to categorize and prioritize tickets.
  - Automatic database classification patching and execution tracing to `agent_traces`.
  - Verification script running a mock ticket end-to-end.
- [ ] **Step 4: Add the rest of the agent chain**
  - Integrate Research Agent, Resolution Agent, and QA Agent nodes.
  - Enforce QA reject retry threshold (escalate to human after 2 tries).
- [ ] **Step 5: Add the human approval step**
  - Implement LangGraph interruption checkpoints.
  - Expose API endpoints for human approval/rejection.
- [ ] **Step 6: Build the dashboard**
  - Streamlit application displaying live ticket feeds, detail traces, and approval controls.
- [ ] **Step 7: Polish it for your portfolio**
  - System performance and security adjustments.

---

## Getting Started

Refer to individual README guides for detailed installation and deployment commands:

1. Setup the Database and REST API: **[Backend README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/README.md)**
2. Setup and run the MCP tools layer: **[MCP Server README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/mcp_server/README.md)**
3. Setup and run the LangGraph workspace: **[Agents README](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/agents/README.md)**