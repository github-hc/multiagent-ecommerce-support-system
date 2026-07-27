from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db import get_db
from app.models.models import Customer, Order, Ticket
from pydantic import BaseModel

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "tier": customer.tier,
        "signup_date": str(customer.signup_date),
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
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
    result = await db.execute(
        select(Order).where(Order.customer_id == customer_id).order_by(Order.order_date.desc())
    )
    orders = result.scalars().all()
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
    result = await db.execute(
        select(Ticket).where(Ticket.customer_id == customer_id).order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().all()
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

from datetime import datetime
from app.models.models import AgentTrace


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
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
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    ticket.category = payload.category
    ticket.priority = payload.priority
    await db.commit()
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
    return {"trace_id": str(trace.id)}

class TicketCreate(BaseModel):
    customer_id: str
    order_id: Optional[str] = None
    channel: str
    subject: Optional[str] = None
    body: str


@router.post("/tickets")
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
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
    return {"ticket_id": str(ticket.id)}

@router.get("/customers")
async def list_customers(limit: int = 5, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).limit(limit))
    customers = result.scalars().all()
    return [{"id": str(c.id), "name": c.name, "email": c.email} for c in customers]