# Backend — FastAPI & PostgreSQL Database Service

This is the FastAPI-based backend and database service for the multi-agent e-commerce support system. It handles relational customer, order, and ticket data, persists execution traces and tool calls for the AI agents, and supports semantic search over a knowledge base using PostgreSQL and `pgvector`.

## Stack

- **FastAPI** — High-performance web framework for APIs
- **SQLAlchemy (async) + Alembic** — Asynchronous Database ORM and migrations
- **PostgreSQL + pgvector** — Relational database with vector similarity search for knowledge base
- **Ollama** — Local LLM runner for embedding generation and agent reasoning
- **Faker** — Synthesizing customer and order data for testing

## Database Schema & Tables

The PostgreSQL database contains the following tables (defined in [models.py](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/app/models/models.py)):

1. **`customers`**: Relational customer table tracking their tier status.
   - Columns: `id` (UUID), `name` (String), `email` (String), `signup_date` (DateTime), `tier` (String, default: "standard")
2. **`orders`**: Historical purchase records.
   - Columns: `id` (UUID), `customer_id` (ForeignKey), `items` (JSON), `amount` (Numeric), `status` (String), `order_date` (DateTime)
3. **`tickets`**: Customer support requests.
   - Columns: `id` (UUID), `customer_id` (ForeignKey), `order_id` (ForeignKey, Optional), `channel` (String), `subject` (String, Optional), `body` (Text), `category` (String, Optional), `priority` (String, Optional), `status` (String, default: "open"), `created_at` (DateTime), `resolved_at` (DateTime, Optional)
4. **`ticket_messages`**: Conversations within a ticket.
   - Columns: `id` (UUID), `ticket_id` (ForeignKey), `sender_type` (String), `content` (Text), `created_at` (DateTime)
5. **`agent_traces`**: Audit logs tracking agent decisions step-by-step.
   - Columns: `id` (UUID), `ticket_id` (ForeignKey), `agent_name` (String), `step_number` (Integer), `input_state` (JSON), `output_state` (JSON), `reasoning_summary` (Text), `created_at` (DateTime)
6. **`tool_calls`**: Audit logs for tools executed by agents.
   - Columns: `id` (UUID), `trace_id` (ForeignKey), `tool_name` (String), `arguments` (JSON), `result` (JSON), `status` (String), `created_at` (DateTime)
7. **`refunds`**: Refund requests requiring authorization.
   - Columns: `id` (UUID), `order_id` (ForeignKey), `ticket_id` (ForeignKey), `amount` (Numeric), `reason` (Text), `status` (String, default: "pending_approval"), `approved_by` (String, Optional), `created_at` (DateTime)
8. **`human_approvals`**: Interruption states waiting on human review.
   - Columns: `id` (UUID), `ticket_id` (ForeignKey), `action_type` (String), `action_ref_id` (UUID, Optional), `status` (String, default: "pending"), `requested_by_agent` (String, Optional), `approved_by` (String, Optional), `created_at` (DateTime)
9. **`kb_docs`**: Knowledge base vector table.
   - Columns: `id` (UUID), `title` (String), `content` (Text), `category` (String, Optional), `embedding` (Vector(768), Optional), `created_at` (DateTime)

## API Endpoints

The backend routes are implemented in [internal.py](file:///Users/harshitchoudhary/Tech2go/Agentic/multi-agent-ecommerce-support/multiagent-ecommerce-support-system/backend/app/routes/internal.py):

| Method | Endpoint | Description |
|---|---|---|
| **GET** | `/health` | Application status check |
| **GET** | `/db-check` | Database connectivity verification |
| **GET** | `/internal/customers` | Lists customers (limited by query param) |
| **GET** | `/internal/customers/{customer_id}` | Fetch a customer profile |
| **GET** | `/internal/orders/{order_id}` | Fetch details of a single order |
| **GET** | `/internal/customers/{customer_id}/orders` | List order history for a customer |
| **GET** | `/internal/customers/{customer_id}/tickets` | List past tickets for a customer |
| **GET** | `/internal/tickets/{ticket_id}` | Retrieve details of a single ticket |
| **POST** | `/internal/tickets` | Create a new customer support ticket |
| **PATCH** | `/internal/tickets/{ticket_id}/classification` | Update ticket category and priority |
| **POST** | `/internal/traces` | Create an execution trace for agent auditing |

---

## Setup & Running Instructions

### 1. Prerequisites

- Python 3.9+
- Docker (for PostgreSQL database)
- [Ollama](https://ollama.com) running locally

### 2. Environment Setup

Create a virtual environment, activate it, and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure your environment file:

```bash
cp .env.example .env
```

Variables configured in `.env`:
- `DATABASE_URL`: Postgres database connection string (e.g. `postgresql://postgres:postgres@localhost:5432/support_db`)
- `OLLAMA_BASE_URL`: Ollama service endpoint (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Target model (default: `llama3.1:8b`)
- `ENV`: Environment descriptor (`development` / `production`)

### 3. Spin Up Postgres Database

Run the database container:

```bash
docker compose up -d
```

> **Note**: If port `5432` is taken, the container redirects to external port `5433`. Update `DATABASE_URL` in `.env` to match.

### 4. Setup Ollama Models

Download the required local LLM and embedding model:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 5. Run Database Migrations & Seeding

Apply Alembic migrations to build tables:

```bash
alembic upgrade head
```

Generate synthetic relational records and knowledge base embeddings:

```bash
python -m seed.generate_data
python -m seed.generate_embeddings
```

This imports mock customer profiles and processes files in `seed/kb_articles/` into vector-embedded documents inside `kb_docs`.

### 6. Start backend API server

Launch FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs**: `http://localhost:8000/docs`
- **Health Check Endpoint**: `http://localhost:8000/health`
- **Database Status Verification**: `http://localhost:8000/db-check`
