import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))


def create_redis_client(decode_responses: bool = True, max_connections: int = 20) -> redis.Redis:
    """
    A client whose pool waits for a free connection instead of opening more.
    The default pool has no limit, so 50 link checks at once can use up every
    connection the free Redis plan allows.
    """
    pool = redis.BlockingConnectionPool.from_url(
        REDIS_URL,
        decode_responses=decode_responses,
        max_connections=max_connections,
        timeout=5,
        socket_connect_timeout=3,
    )
    return redis.Redis.from_pool(pool)


# Centralized async Redis client instance
redis_client = create_redis_client()
