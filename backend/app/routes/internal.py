from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Customer, Order, Ticket

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