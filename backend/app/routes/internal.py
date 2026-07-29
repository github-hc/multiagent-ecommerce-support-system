from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import asyncio

from app.db import get_db
from app.models.models import Customer, Order, Ticket, AgentTrace, KBDoc, Refund, HumanApproval, TicketMessage
from pydantic import BaseModel
from app.logger import logger
import ollama

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching customer profile for customer_id: {customer_id}")
    customer = await db.get(Customer, customer_id)
    if not customer:
        logger.warning(f"Customer profile not found for customer_id: {customer_id}")
        raise HTTPException(status_code=404, detail="customer not found")
    logger.info(f"Successfully retrieved customer profile for customer_id: {customer_id} ({customer.name})")
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "tier": customer.tier,
        "signup_date": str(customer.signup_date),
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching order details for order_id: {order_id}")
    order = await db.get(Order, order_id)
    if not order:
        logger.warning(f"Order not found for order_id: {order_id}")
        raise HTTPException(status_code=404, detail="order not found")
    logger.info(f"Successfully retrieved order details for order_id: {order_id}")
    return {
        "id": str(order.id),
        "customer_id": str(order.customer_id),
        "items": order.items,
        "amount": float(order.amount),
        "status": order.status,
        "order_date": str(order.order_date),
    }


@router.get("/customers/{customer_id}/orders")
async def get_customer_orders(customer_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching order history for customer_id: {customer_id}")
    result = await db.execute(
        select(Order).where(Order.customer_id == customer_id).order_by(Order.order_date.desc())
    )
    orders = result.scalars().all()
    logger.info(f"Retrieved {len(orders)} orders for customer_id: {customer_id}")
    return [
        {
            "id": str(o.id),
            "items": o.items,
            "amount": float(o.amount),
            "status": o.status,
            "order_date": str(o.order_date),
        }
        for o in orders
    ]


@router.get("/customers/{customer_id}/tickets")
async def get_customer_tickets(customer_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching support ticket history for customer_id: {customer_id}")
    result = await db.execute(
        select(Ticket).where(Ticket.customer_id == customer_id).order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().all()
    logger.info(f"Retrieved {len(tickets)} tickets for customer_id: {customer_id}")
    return [
        {
            "id": str(t.id),
            "subject": t.subject,
            "category": t.category,
            "status": t.status,
            "created_at": str(t.created_at),
        }
        for t in tickets
    ]


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching details for ticket_id: {ticket_id}")
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        logger.warning(f"Ticket not found for ticket_id: {ticket_id}")
        raise HTTPException(status_code=404, detail="ticket not found")
    logger.info(f"Successfully retrieved ticket details for ticket_id: {ticket_id}")
    return {
        "id": str(ticket.id),
        "customer_id": str(ticket.customer_id),
        "order_id": str(ticket.order_id) if ticket.order_id else None,
        "subject": ticket.subject,
        "body": ticket.body,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
    }


class TicketClassification(BaseModel):
    category: str
    priority: str


@router.patch("/tickets/{ticket_id}/classification")
async def classify_ticket(ticket_id: str, payload: TicketClassification, db: AsyncSession = Depends(get_db)):
    logger.info(f"Updating classification for ticket_id: {ticket_id} | category: {payload.category}, priority: {payload.priority}")
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        logger.warning(f"Failed to classify. Ticket not found: {ticket_id}")
        raise HTTPException(status_code=404, detail="ticket not found")
    ticket.category = payload.category
    ticket.priority = payload.priority
    await db.commit()
    logger.info(f"Successfully classified ticket_id: {ticket_id} as {payload.category}/{payload.priority}")
    return {"ticket_id": ticket_id, "category": ticket.category, "priority": ticket.priority}


class TraceCreate(BaseModel):
    ticket_id: str
    agent_name: str
    step_number: int
    input_state: dict
    output_state: dict
    reasoning_summary: str


@router.post("/traces")
async def create_trace(payload: TraceCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Creating trace log entry | ticket_id: {payload.ticket_id} | agent: {payload.agent_name} | step: {payload.step_number}")
    trace = AgentTrace(
        ticket_id=payload.ticket_id,
        agent_name=payload.agent_name,
        step_number=payload.step_number,
        input_state=payload.input_state,
        output_state=payload.output_state,
        reasoning_summary=payload.reasoning_summary,
    )
    db.add(trace)
    await db.commit()
    logger.info(f"Successfully created trace ID {trace.id} for ticket_id: {payload.ticket_id}")
    return {"trace_id": str(trace.id)}


class TicketCreate(BaseModel):
    customer_id: str
    order_id: Optional[str] = None
    channel: str
    subject: Optional[str] = None
    body: str


@router.post("/tickets")
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Creating new ticket for customer_id: {payload.customer_id} | channel: {payload.channel}")
    ticket = Ticket(
        customer_id=payload.customer_id,
        order_id=payload.order_id,
        channel=payload.channel,
        subject=payload.subject,
        body=payload.body,
        status="open",
    )
    db.add(ticket)
    await db.commit()
    logger.info(f"Successfully created ticket_id: {ticket.id} for customer_id: {payload.customer_id}")
    return {"ticket_id": str(ticket.id)}


@router.get("/customers")
async def list_customers(limit: int = 5, db: AsyncSession = Depends(get_db)):
    logger.info(f"Listing customers (limit={limit})")
    result = await db.execute(select(Customer).limit(limit))
    customers = result.scalars().all()
    logger.info(f"Retrieved {len(customers)} customers (requested limit={limit})")
    return [{"id": str(c.id), "name": c.name, "email": c.email} for c in customers]


@router.get("/kb/search")
async def search_kb(query: str, limit: int = 3, db: AsyncSession = Depends(get_db)):
    logger.info(f"KB Search query received: '{query}' | limit: {limit}")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = ollama.embeddings(model="nomic-embed-text", prompt=query)
            embedding = response["embedding"]
            result = await db.execute(
                select(KBDoc)
                .order_by(KBDoc.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            docs = result.scalars().all()
            logger.info(f"KB Search returned {len(docs)} matching articles.")
            return [
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "content": doc.content,
                    "category": doc.category,
                }
                for doc in docs
            ]
        except Exception as e:
            err_str = str(e)
            # Retry on transient DB startup/recovery errors
            is_transient = any(msg in err_str for msg in [
                "CannotConnectNowError",
                "recovery mode",
                "connection refused",
                "could not connect",
            ])
            if is_transient and attempt < max_retries:
                wait = attempt * 2  # 2s, 4s
                logger.warning(
                    f"KB Search: transient DB error on attempt {attempt}/{max_retries}, "
                    f"retrying in {wait}s... Error: {e}"
                )
                await asyncio.sleep(wait)
                continue
            logger.error(f"Error searching knowledge base: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


class RefundCreate(BaseModel):
    order_id: str
    ticket_id: str
    amount: float
    reason: Optional[str] = None


@router.post("/refunds")
async def create_refund(payload: RefundCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Creating refund request for order_id: {payload.order_id} | ticket_id: {payload.ticket_id} | amount: {payload.amount}")
    try:
        refund = Refund(
            order_id=payload.order_id,
            ticket_id=payload.ticket_id,
            amount=payload.amount,
            reason=payload.reason,
            status="pending_approval",
        )
        db.add(refund)
        await db.flush()
        
        approval = HumanApproval(
            ticket_id=payload.ticket_id,
            action_type="refund",
            action_ref_id=refund.id,
            status="pending",
            requested_by_agent="resolution_agent",
        )
        db.add(approval)
        await db.commit()
        
        logger.info(f"Successfully created refund ID {refund.id} and approval request ID {approval.id}")
        return {
            "status": "success",
            "refund_id": str(refund.id),
            "approval_id": str(approval.id),
        }
    except Exception as e:
        logger.error(f"Error creating refund request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class MessageCreate(BaseModel):
    sender_type: str
    content: str


@router.post("/tickets/{ticket_id}/messages")
async def add_ticket_message(ticket_id: str, payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adding ticket message for ticket_id: {ticket_id} | sender: {payload.sender_type}")
    try:
        message = TicketMessage(
            ticket_id=ticket_id,
            sender_type=payload.sender_type,
            content=payload.content
        )
        db.add(message)
        await db.commit()
        logger.info(f"Successfully added message ID {message.id} to ticket_id: {ticket_id}")
        return {"message_id": str(message.id)}
    except Exception as e:
        logger.error(f"Error adding message to ticket_id {ticket_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class StatusUpdate(BaseModel):
    status: str


@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, payload: StatusUpdate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Updating status for ticket_id: {ticket_id} to '{payload.status}'")
    try:
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            logger.warning(f"Ticket not found for status update: {ticket_id}")
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        ticket.status = payload.status
        if payload.status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Successfully updated status for ticket_id: {ticket_id} to '{payload.status}'")
        return {"status": "success", "ticket_id": ticket_id, "new_status": payload.status}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating status for ticket_id {ticket_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))