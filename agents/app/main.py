import logging
import traceback
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langgraph.errors import GraphInterrupt
from app.config import settings
from app.graph.graph import build_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncNullConnectionPool
from psycopg.rows import dict_row
import app.logger

logger = logging.getLogger("agents-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing persistent Agents Service...")
    # AsyncNullConnectionPool: opens a fresh connection per call and closes it
    # immediately — avoids idle connection timeouts during long LLM calls.
    pool = AsyncNullConnectionPool(
        conninfo=settings.database_url,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}
    )
    async with pool:
        saver = AsyncPostgresSaver(pool)
        logger.info("Connecting and setting up checkpointer database tables...")
        await saver.setup()

        # Compile graph with the async checkpointer
        app.state.graph = build_graph(saver)
        logger.info("Graph compiled successfully with Postgres checkpointer.")
        yield
    logger.info("Agents Service shutting down...")


app = FastAPI(title="Agents Service", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Global exception handler — turns any unhandled exception inside a route
# into a structured JSON 500 with a human-readable error message and the
# full traceback in the logs.  Without this FastAPI returns an opaque
# {"detail":"Internal Server Error"} that gives no clue about the real cause.
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        f"Unhandled exception on {request.method} {request.url}\n{tb}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "path": str(request.url),
        },
    )


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: str, request: Request):
    """Run the full agent workflow for a ticket.

    The graph normally runs to END in a single ainvoke() call (MVP mode).
    If interrupt_before=["human_approval"] is active in graph.py the graph
    will pause here and return status="paused"; the caller should then POST
    to /tickets/{id}/resume with the human decision.
    """
    logger.info(f"Run request received for ticket_id: {ticket_id}")

    # --- fetch ticket from backend ---
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.backend_base_url}/internal/tickets/{ticket_id}"
            )
            resp.raise_for_status()
            ticket = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend returned {e.response.status_code} for ticket {ticket_id}")
        return JSONResponse(
            status_code=502,
            content={"error": "BackendError", "detail": str(e)},
        )

    initial_state = {
        "ticket_id": ticket["id"],
        "customer_id": ticket["customer_id"],
        "order_id": ticket["order_id"],
        "subject": ticket["subject"],
        "body": ticket["body"],
        "category": None,
        "priority": None,
        "kb_results": [],
        "draft_response": None,
        "qa_feedback": None,
        "qa_approved": False,
        "iteration_count": 0,
        "requires_human_approval": False,
    }

    config = {"configurable": {"thread_id": ticket_id}}

    # --- invoke graph ---
    try:
        result = await request.app.state.graph.ainvoke(initial_state, config=config)
    except GraphInterrupt:
        # Graph paused via interrupt_before — check state and report context
        logger.info(f"Graph paused for ticket_id: {ticket_id}")
        graph_state = await request.app.state.graph.aget_state(config)
        interrupt_info = []
        for task in graph_state.tasks:
            for item in getattr(task, "interrupts", []):
                interrupt_info.append(
                    item.value if hasattr(item, "value") else str(item)
                )
        if "human_approval" in (graph_state.next or []) and not interrupt_info:
            interrupt_info = ["refund requested - needs human approval"]
        return {"status": "paused", "interrupt": interrupt_info}
    except Exception as e:
        # Graph raised an unexpected error — log with full traceback and
        # return a structured 500 so the caller knows what actually failed.
        tb = traceback.format_exc()
        logger.error(
            f"Graph execution failed for ticket_id: {ticket_id}\n"
            f"Error: {type(e).__name__}: {e}\n{tb}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": type(e).__name__,
                "detail": str(e),
                "ticket_id": ticket_id,
            },
        )

    # --- check if graph paused without raising GraphInterrupt (interrupt_before) ---
    graph_state = await request.app.state.graph.aget_state(config)
    if graph_state.next:
        logger.info(f"Graph paused on node(s): {graph_state.next} for ticket_id: {ticket_id}")
        interrupt_info = []
        for task in graph_state.tasks:
            for item in getattr(task, "interrupts", []):
                interrupt_info.append(
                    item.value if hasattr(item, "value") else str(item)
                )
        if "human_approval" in graph_state.next and not interrupt_info:
            interrupt_info = ["refund requested - needs human approval"]
        return {"status": "paused", "interrupt": interrupt_info}

    logger.info(f"Ticket run completed for ticket_id: {ticket_id}")
    return {"status": "completed", "result": result}


@app.post("/tickets/{ticket_id}/resume")
async def resume_ticket(ticket_id: str, decision: dict, request: Request):
    """Resume a paused ticket after human review.

    Send: {"approved": true} or {"approved": false, "note": "reason"}

    MVP NOTE: This is a no-op if MVP_AUTO_APPROVE=True in human_approval.py
    (graph never pauses).  Flip that flag + re-enable interrupt_before in
    graph.py to activate the real human-in-the-loop path.
    """
    logger.info(f"Resume request received for ticket_id: {ticket_id} | decision: {decision}")
    config = {"configurable": {"thread_id": ticket_id}}

    # Verify the graph is actually paused before trying to resume
    graph_state = await request.app.state.graph.aget_state(config)
    if not graph_state.next:
        logger.warning(
            f"Resume called for ticket_id: {ticket_id} but graph is not paused "
            "(MVP_AUTO_APPROVE may be True). Returning noop."
        )
        return {"status": "noop", "message": "Graph is not paused — nothing to resume."}

    # Inject the human decision into the graph state
    if decision.get("approved"):
        await request.app.state.graph.aupdate_state(
            config,
            {"qa_approved": True, "requires_human_approval": False},
            as_node="human_approval",
        )
    else:
        note = decision.get("note", "Human rejected the request")
        await request.app.state.graph.aupdate_state(
            config,
            {"qa_approved": False, "qa_feedback": note, "requires_human_approval": False},
            as_node="human_approval",
        )

    try:
        result = await request.app.state.graph.ainvoke(None, config=config)
    except GraphInterrupt:
        logger.info(f"Graph paused again after resume for ticket_id: {ticket_id}")
        graph_state = await request.app.state.graph.aget_state(config)
        interrupt_info = []
        for task in graph_state.tasks:
            for item in getattr(task, "interrupts", []):
                interrupt_info.append(
                    item.value if hasattr(item, "value") else str(item)
                )
        return {"status": "paused", "interrupt": interrupt_info}
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(
            f"Graph resume failed for ticket_id: {ticket_id}\n"
            f"Error: {type(e).__name__}: {e}\n{tb}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": type(e).__name__,
                "detail": str(e),
                "ticket_id": ticket_id,
            },
        )

    # Check if it paused again (e.g. second interrupt)
    graph_state = await request.app.state.graph.aget_state(config)
    if graph_state.next:
        logger.info(f"Graph paused after resume on: {graph_state.next} for ticket_id: {ticket_id}")
        interrupt_info = []
        for task in graph_state.tasks:
            for item in getattr(task, "interrupts", []):
                interrupt_info.append(
                    item.value if hasattr(item, "value") else str(item)
                )
        return {"status": "paused", "interrupt": interrupt_info}

    logger.info(f"Ticket resume completed for ticket_id: {ticket_id}")
    return {"status": "completed", "result": result}


@app.get("/health")
def health():
    return {"status": "ok"}