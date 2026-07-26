import asyncio
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from sqlalchemy import text

from app.db import async_session, engine, Base
from app.models.models import Customer, Order, KBDoc

fake = Faker()

PRODUCT_CATALOG = [
    {"sku": "SKU-001", "name": "Wireless Mouse", "price": 25.99},
    {"sku": "SKU-002", "name": "Mechanical Keyboard", "price": 89.99},
    {"sku": "SKU-003", "name": "USB-C Hub", "price": 34.50},
    {"sku": "SKU-004", "name": "Laptop Stand", "price": 45.00},
    {"sku": "SKU-005", "name": "Noise Cancelling Headphones", "price": 199.99},
]

ORDER_STATUSES = ["placed", "shipped", "delivered", "returned"]


async def seed_customers(session, count=20):
    customers = []
    for _ in range(count):
        c = Customer(
            id=uuid.uuid4(),
            name=fake.name(),
            email=fake.email(),
            signup_date=fake.date_between(start_date="-2y", end_date="today"),
            tier=random.choice(["standard", "standard", "standard", "premium"]),
        )
        session.add(c)
        customers.append(c)
    await session.commit()
    return customers


async def seed_orders(session, customers, count=40):
    orders = []
    for _ in range(count):
        customer = random.choice(customers)
        items = random.sample(PRODUCT_CATALOG, k=random.randint(1, 3))
        amount = sum(item["price"] for item in items)
        o = Order(
            id=uuid.uuid4(),
            customer_id=customer.id,
            items=items,
            amount=amount,
            status=random.choice(ORDER_STATUSES),
            order_date=fake.date_time_between(start_date="-90d", end_date="now"),
        )
        session.add(o)
        orders.append(o)
    await session.commit()
    return orders


async def seed_kb_docs(session):
    kb_dir = Path(__file__).parent / "kb_articles"
    for file in kb_dir.glob("*.md"):
        content = file.read_text()
        title = content.split("\n")[0].replace("#", "").strip()
        doc = KBDoc(
            id=uuid.uuid4(),
            title=title,
            content=content,
            category=file.stem,
        )
        session.add(doc)
    await session.commit()


async def main():
    async with async_session() as session:
        print("Seeding customers...")
        customers = await seed_customers(session)

        print("Seeding orders...")
        await seed_orders(session, customers)

        print("Seeding knowledge base docs...")
        await seed_kb_docs(session)

        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())