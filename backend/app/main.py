from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db import get_db
from app.routes import internal
from app.logger import logger

app = FastAPI(title="Ecommerce Multiagent Support")
logger.info("Initializing FastAPI Ecommerce Multiagent Support application...")
app.include_router(internal.router)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint triggered.")
    return {"status": "ok", "env": settings.env}

@app.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    logger.info("DB connectivity check triggered. Querying database...")
    try:
        result = await db.execute(text("SELECT 1"))
        val = result.scalar()
        logger.info("DB connectivity successful.")
        return {"db_status": "connected", "result": val}
    except Exception as e:
        logger.error(f"DB connectivity check failed: {e}", exc_info=True)
        raise e