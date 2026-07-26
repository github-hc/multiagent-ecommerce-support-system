from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db import get_db
from app.routes import internal

app = FastAPI(title="Ecommerce Multiagent Support")
app.include_router(internal.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.env}

@app.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db_status": "connected", "result": result.scalar()}