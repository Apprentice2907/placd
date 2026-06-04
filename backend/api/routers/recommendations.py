"""
Placd — Job Recommendation Engine

Endpoints:
  GET  /api/recommendations?limit=10   — content-based recommendations via pgvector
  POST /api/recommendations/view/{job_id} — record a job view in Redis
"""

import json
import os
from uuid import uuid4

import structlog
from fastapi import APIRouter, Request
from sqlalchemy import text

from db.connection import AsyncSessionLocal

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
VIEW_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _get_session_id(request: Request) -> str:
    """Derive a session identifier from cookie or generate one."""
    return request.cookies.get("placd_session", str(uuid4()))


async def _get_redis():
    try:
        import redis.asyncio as aioredis
        return await aioredis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


# ─── Record view ─────────────────────────────────────────────────────────────

@router.post("/view/{job_id}")
async def record_view(job_id: str, request: Request):
    session_id = _get_session_id(request)
    redis = await _get_redis()
    if redis:
        key = f"user:{session_id}:views"
        async with redis:
            await redis.lpush(key, job_id)
            await redis.ltrim(key, 0, 49)      # keep last 50 views
            await redis.expire(key, VIEW_TTL_SECONDS)
    return {"recorded": True}


# ─── Get recommendations ─────────────────────────────────────────────────────

@router.get("")
async def get_recommendations(request: Request, limit: int = 10):
    session_id = _get_session_id(request)
    redis = await _get_redis()

    viewed_ids: list[str] = []
    if redis:
        async with redis:
            viewed_ids = await redis.lrange(f"user:{session_id}:views", 0, 9)

    if not viewed_ids:
        # Cold start — return newest active jobs
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT j.id, j.title, j.location, j.apply_url, j.created_at,
                           j.is_remote, j.status, j.freshness_score,
                           c.name as company, c.logo_url as company_logo_url
                    FROM jobs j
                    LEFT JOIN companies c ON j.company_id = c.id
                    WHERE j.status = 'active'
                    ORDER BY j.freshness_score DESC NULLS LAST, j.created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            rows = result.fetchall()
        return {
            "recommendations": [dict(r._mapping) for r in rows],
            "reason": "cold_start",
            "based_on": None,
        }

    # Try pgvector nearest-neighbor from avg embedding
    try:
        async with AsyncSessionLocal() as session:
            # Compute average embedding of viewed jobs
            placeholders = ", ".join(f"'{jid}'" for jid in viewed_ids)
            avg_result = await session.execute(
                text(f"""
                    SELECT AVG(description_embedding) as avg_emb
                    FROM jobs
                    WHERE id::text IN ({placeholders})
                      AND description_embedding IS NOT NULL
                """)
            )
            avg_row = avg_result.fetchone()

            if avg_row and avg_row.avg_emb is not None:
                exclude_clause = ", ".join(f"'{jid}'" for jid in viewed_ids)
                reco_result = await session.execute(
                    text(f"""
                        SELECT j.id, j.title, j.location, j.apply_url, j.created_at,
                               j.is_remote, j.status, j.freshness_score,
                               1 - (j.description_embedding <=> :avg_emb::vector) as similarity,
                               c.name as company, c.logo_url as company_logo_url
                        FROM jobs j
                        LEFT JOIN companies c ON j.company_id = c.id
                        WHERE j.status = 'active'
                          AND j.id::text NOT IN ({exclude_clause})
                          AND j.description_embedding IS NOT NULL
                        ORDER BY j.description_embedding <=> :avg_emb::vector
                        LIMIT :limit
                    """),
                    {"avg_emb": avg_row.avg_emb, "limit": limit},
                )
                rows = reco_result.fetchall()

                # Get title of most recently viewed for "because you viewed" label
                ref_result = await session.execute(
                    text("SELECT title, c.name as company FROM jobs j LEFT JOIN companies c ON j.company_id = c.id WHERE j.id::text = :id"),
                    {"id": viewed_ids[0]},
                )
                ref = ref_result.fetchone()
                based_on = f"{ref.title} at {ref.company}" if ref else None

                return {
                    "recommendations": [dict(r._mapping) for r in rows],
                    "reason": "embedding_similarity",
                    "based_on": based_on,
                }
    except Exception as e:
        logger.warning("pgvector_recommendation_failed", error=str(e))

    # Fallback — freshness-based
    async with AsyncSessionLocal() as session:
        exclude_clause = ", ".join(f"'{jid}'" for jid in viewed_ids)
        result = await session.execute(
            text(f"""
                SELECT j.id, j.title, j.location, j.apply_url, j.created_at,
                       j.is_remote, j.status, j.freshness_score,
                       c.name as company, c.logo_url as company_logo_url
                FROM jobs j
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE j.status = 'active'
                  AND j.id::text NOT IN ({exclude_clause})
                ORDER BY j.freshness_score DESC NULLS LAST
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()

    return {
        "recommendations": [dict(r._mapping) for r in rows],
        "reason": "freshness_fallback",
        "based_on": None,
    }
