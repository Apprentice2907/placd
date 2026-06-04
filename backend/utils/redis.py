import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

# Centralized async Redis client instance
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
