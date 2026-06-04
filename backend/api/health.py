import asyncio
from fastapi import APIRouter, Response
from sqlalchemy import text
from db.connection import AsyncSessionLocal
from utils.redis import redis_client
from celery.app.control import Inspect
from workers.crawlers import celery as celery_app # Adjust this if celery app is instantiated elsewhere

router = APIRouter()

@router.get("/api/health")
async def health_check(response: Response):
    """Deep health check for DB, Redis, and Celery."""
    status = "healthy"
    
    # Check Postgres
    postgres_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            postgres_ok = True
    except Exception:
        status = "degraded"
        
    # Check Redis
    redis_ok = False
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        status = "degraded"
        
    # Check Celery Workers
    workers_count = 0
    try:
        i = Inspect(app=celery_app)
        active = i.active()
        if active:
            workers_count = len(active)
    except Exception:
        # Don't necessarily degrade overall status if celery ping fails in some envs
        pass
        
    if status == "degraded":
        response.status_code = 503
        
    return {
        "status": status,
        "postgres": postgres_ok,
        "redis": redis_ok,
        "workers": workers_count
    }
