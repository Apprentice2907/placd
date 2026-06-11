"""
Placd — Startup Health Checks

Verifies PostgreSQL, pgvector, Redis, and required env vars on application boot.
Raises clearly if any dependency is unreachable or misconfigured.

Usage:
    from utils.startup_check import run_startup_checks

    # In FastAPI startup:
    @app.on_event("startup")
    async def startup():
        await run_startup_checks()
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text

logger = logging.getLogger(__name__)

TYPESENSE_ENABLED = os.getenv("TYPESENSE_ENABLED", "true").lower() == "true"
REQUIRED_ENV_VARS = ["DATABASE_URL", "REDIS_URL", "GEMINI_API_KEY"]
if TYPESENSE_ENABLED:
    REQUIRED_ENV_VARS.append("TYPESENSE_API_KEY")


class StartupCheckFailed(RuntimeError):
    """Raised when a critical dependency is unreachable at boot time."""
    pass


async def check_postgres() -> None:
    """
    Verify PostgreSQL is reachable and responding.
    Raises StartupCheckFailed with a clear message if not.
    """
    from db.connection import engine

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            if value != 1:
                raise StartupCheckFailed(
                    "PostgreSQL health check returned unexpected value. "
                    "Expected SELECT 1 to return 1."
                )
        logger.info("✓ PostgreSQL connection verified")
    except StartupCheckFailed:
        raise
    except Exception as exc:
        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/placd")
        # Mask password in error message
        safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
        raise StartupCheckFailed(
            f"Cannot connect to PostgreSQL at {safe_url}.\n"
            f"Ensure the database is running and DATABASE_URL is correct.\n"
            f"Error: {exc}"
        ) from exc


async def check_pgvector() -> None:
    """
    Verify the pgvector extension is installed in the database.
    Required for embedding-based semantic search.
    Raises StartupCheckFailed if the extension is missing.
    """
    from db.connection import engine

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            row = result.fetchone()
            if not row:
                raise StartupCheckFailed(
                    "pgvector extension is NOT installed.\n"
                    "Run: CREATE EXTENSION IF NOT EXISTS vector;\n"
                    "Semantic search and embedding features will not work without it."
                )
        logger.info("✓ pgvector extension verified")
    except StartupCheckFailed:
        raise
    except Exception as exc:
        raise StartupCheckFailed(
            f"Failed to check pgvector extension.\n"
            f"Error: {exc}"
        ) from exc


async def check_redis() -> None:
    """
    Verify Redis is reachable and responding.
    Raises StartupCheckFailed with a clear message if not.
    """
    import redis.asyncio as aioredis

    redis_url = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

    try:
        client = aioredis.from_url(redis_url, decode_responses=True)
        pong = await client.ping()
        if not pong:
            raise StartupCheckFailed(
                "Redis health check failed — PING did not return PONG."
            )
        await client.aclose()
        logger.info("✓ Redis connection verified")
    except StartupCheckFailed:
        raise
    except Exception as exc:
        # Mask password in Redis URL
        safe_url = redis_url.split("@")[-1] if "@" in redis_url else redis_url
        raise StartupCheckFailed(
            f"Cannot connect to Redis at {safe_url}.\n"
            f"Ensure Redis is running and REDIS_URL is correct.\n"
            f"Error: {exc}"
        ) from exc


async def check_typesense() -> None:
    """
    Verify Typesense is reachable and responding.
    Raises StartupCheckFailed if not.
    """
    if not TYPESENSE_ENABLED:
        logger.info("✓ Typesense connection check skipped (TYPESENSE_ENABLED=false)")
        return

    from search.typesense_sync import typesense_sync
    import asyncio
    
    def _ping():
        return typesense_sync.client.operations.is_healthy()
        
    try:
        healthy = await asyncio.to_thread(_ping)
        if not healthy:
            raise StartupCheckFailed("Typesense health check returned false")
        logger.info("✓ Typesense connection verified")
    except StartupCheckFailed:
        raise
    except Exception as exc:
        raise StartupCheckFailed(
            f"Cannot connect to Typesense.\n"
            f"Ensure the typesense container is running.\n"
            f"Error: {exc}"
        ) from exc


async def check_env_vars() -> None:
    """
    Verify all required environment variables are set and non-empty.
    Raises StartupCheckFailed listing any missing vars.
    """
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var, "").strip()]

    if missing:
        raise StartupCheckFailed(
            f"Missing required environment variables: {', '.join(missing)}.\n"
            f"Set them in your .env file or environment before starting the application."
        )

    logger.info("✓ Required environment variables verified: %s", ", ".join(REQUIRED_ENV_VARS))


async def run_startup_checks() -> dict:
    """
    Run all startup health checks and return a status dict.
    Raises StartupCheckFailed on first failure — never falls back silently.
    """
    results = {}

    await check_env_vars()
    results["env_vars"] = "ok"

    await check_postgres()
    results["postgres"] = "ok"

    await check_pgvector()
    results["pgvector"] = "ok"

    await check_redis()
    results["redis"] = "ok"

    await check_typesense()
    results["typesense"] = "ok"

    logger.info("All startup checks passed: %s", results)
    return results


# Keep backward-compatible alias
run_all_checks = run_startup_checks


if __name__ == "__main__":
    import asyncio

    async def main():
        try:
            status = await run_startup_checks()
            print(f"[OK] All checks passed: {status}")
        except StartupCheckFailed as e:
            print(f"[FATAL] Startup check failed:\n{e}")
            exit(1)

    asyncio.run(main())
