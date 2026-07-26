# multiagent-ecommerce-support-system

# Backend — Ecommerce Multiagent Support

FastAPI + LangGraph backend for the multi-agent e-commerce support system.
Agents run locally via Ollama; data lives in PostgreSQL (with pgvector for
knowledge base search).

## Stack

- **FastAPI** — HTTP API
- **SQLAlchemy (async) + Alembic** — database models & migrations
- **PostgreSQL + pgvector** — relational data + vector search for the knowledge base
- **Ollama** — local LLM for agent reasoning + embeddings (no external API needed)
- **LangGraph** — multi-agent orchestration (added in later steps)

## Prerequisites

- Python 3.11+
- Docker (for Postgres)
- [Ollama](https://ollama.com) installed and running locally

## Setup

### 1. Clone and create a virtual environment

\`\`\`bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
\`\`\`

### 2. Install dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Environment variables

Copy the example file and fill in real values:

\`\`\`bash
cp .env.example .env
\`\`\`

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `OLLAMA_BASE_URL` | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Model used for agent reasoning (e.g. `llama3.1:8b`) |
| `ENV` | `development` / `production` |

### 4. Start PostgreSQL

From the repo root (where `docker-compose.yml` lives):

\`\`\`bash
docker compose up -d
\`\`\`

> If port 5432 is already in use locally, the compose file maps it to 5433 instead —
> make sure `DATABASE_URL` in `.env` matches whichever port you're using.

### 5. Pull required Ollama models

\`\`\`bash
ollama pull llama3.1:8b        # agent reasoning
ollama pull nomic-embed-text   # knowledge base embeddings
\`\`\`

### 6. Run database migrations

\`\`\`bash
alembic upgrade head
\`\`\`

### 7. Seed the database

\`\`\`bash
python -m seed.generate_data
python -m seed.generate_embeddings
\`\`\`

This populates fake customers/orders (via Faker) and embeds the knowledge
base articles in `seed/kb_articles/` for vector search.

### 8. Run the server

\`\`\`bash
uvicorn app.main:app --reload --port 8000
\`\`\`

- Health check: `http://localhost:8000/health`
- DB connection check: `http://localhost:8000/db-check`
- Interactive API docs: `http://localhost:8000/docs`

## Project structure

\`\`\`
backend/
├── app/
│   ├── main.py          # FastAPI entrypoint
│   ├── config.py        # settings loaded from .env
│   ├── db.py            # SQLAlchemy engine/session setup
│   ├── models/          # SQLAlchemy models (customers, orders, tickets, etc.)
│   ├── graph/           # LangGraph agent nodes (added in later steps)
│   └── routes/          # API route modules
├── alembic/              # DB migrations
├── seed/
│   ├── generate_data.py       # fake customers/orders
│   ├── generate_embeddings.py # embeds KB articles
│   └── kb_articles/           # policy docs used by the Research Agent
├── requirements.txt
├── .env.example
└── README.md
\`\`\`

## Status

- [x] Environment + FastAPI skeleton
- [x] PostgreSQL + SQLAlchemy connection
- [x] Database models + Alembic migrations
- [x] Seed data (customers, orders, KB articles)
- [x] Knowledge base embeddings (pgvector + Ollama)
- [ ] MCP server (tools for agents)
- [ ] LangGraph agent chain (triage → research → resolution → QA)
- [ ] Human-in-the-loop approval flow
- [ ] Dashboard