"""
Placd — Saved Searches + SSE Alerts

Endpoints:
  POST /api/alerts/saved-searches       — save a search
  GET  /api/alerts/saved-searches       — list saved searches
  DELETE /api/alerts/saved-searches/{id} — delete
  GET  /api/alerts/stream               — SSE new-job stream
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

from db.connection import AsyncSessionLocal

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ─── Models ──────────────────────────────────────────────────────────────────

class SavedSearchCreate(BaseModel):
    name: str
    filters: dict
    notification: str = "none"  # "browser" | "email" | "none"


class SavedSearch(BaseModel):
    id: str
    name: str
    filters: dict
    notification: str
    created_at: str
    last_notified_at: str | None
    match_count: int


# ─── Ensure saved_searches table exists ─────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_searches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    filters JSONB NOT NULL DEFAULT '{}',
    notification TEXT NOT NULL DEFAULT 'none',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_notified_at TIMESTAMPTZ,
    match_count INTEGER NOT NULL DEFAULT 0,
    session_id TEXT
);
"""


async def ensure_table():
    async with AsyncSessionLocal() as session:
        await session.execute(text(CREATE_TABLE_SQL))
        await session.commit()


# ─── CRUD Routes ─────────────────────────────────────────────────────────────

@router.post("/saved-searches", response_model=dict)
async def create_saved_search(body: SavedSearchCreate):
    await ensure_table()
    new_id = str(uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO saved_searches (id, name, filters, notification, created_at)
                VALUES (:id, :name, :filters, :notification, NOW())
            """),
            {
                "id": new_id,
                "name": body.name,
                "filters": json.dumps(body.filters),
                "notification": body.notification,
            },
        )
        await session.commit()
    logger.info("saved_search_created", id=new_id, name=body.name)
    return {"id": new_id, "message": "Saved search created"}


@router.get("/saved-searches")
async def list_saved_searches():
    await ensure_table()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM saved_searches ORDER BY created_at DESC LIMIT 100")
        )
        rows = result.fetchall()
    return [
        {
            "id": r.id,
            "name": r.name,
            "filters": r.filters if isinstance(r.filters, dict) else json.loads(r.filters),
            "notification": r.notification,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_notified_at": r.last_notified_at.isoformat() if r.last_notified_at else None,
            "match_count": r.match_count,
        }
        for r in rows
    ]


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str):
    await ensure_table()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("DELETE FROM saved_searches WHERE id = :id RETURNING id"),
            {"id": search_id},
        )
        deleted = result.fetchone()
        await session.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Deleted"}


# ─── SSE Stream ──────────────────────────────────────────────────────────────

async def _sse_generator(search_id: str) -> AsyncGenerator[str, None]:
    """Poll every 30s for new jobs matching the saved search."""
    last_check = datetime.now(timezone.utc)

    # Send initial heartbeat
    yield "event: connected\ndata: {}\n\n"

    try:
        while True:
            await asyncio.sleep(30)

            async with AsyncSessionLocal() as session:
                # Get saved search filters
                result = await session.execute(
                    text("SELECT filters FROM saved_searches WHERE id = :id"),
                    {"id": search_id},
                )
                row = result.fetchone()
                if not row:
                    yield "event: error\ndata: {\"message\": \"Search not found\"}\n\n"
                    return

                filters = row.filters if isinstance(row.filters, dict) else json.loads(row.filters)
                q = filters.get("q", "")

                # Query for new jobs since last check
                sql = """
                    SELECT id, title, company_name, apply_url, created_at
                    FROM jobs j
                    LEFT JOIN companies c ON j.company_id = c.id
                    WHERE j.created_at > :last_check
                      AND j.status = 'active'
                """
                params: dict = {"last_check": last_check}
                if q:
                    sql += " AND (j.title ILIKE :q OR c.name ILIKE :q)"
                    params["q"] = f"%{q}%"
                sql += " ORDER BY j.created_at DESC LIMIT 20"

                new_result = await session.execute(text(sql), params)
                new_jobs = new_result.fetchall()

                # Update last_notified_at
                if new_jobs:
                    await session.execute(
                        text("UPDATE saved_searches SET last_notified_at = NOW(), match_count = match_count + :count WHERE id = :id"),
                        {"count": len(new_jobs), "id": search_id},
                    )
                    await session.commit()

                    payload = json.dumps({
                        "count": len(new_jobs),
                        "jobs": [
                            {
                                "id": str(j.id),
                                "title": j.title,
                                "company": j.company_name,
                                "apply_url": j.apply_url,
                            }
                            for j in new_jobs[:5]
                        ],
                    })
                    yield f"event: new_jobs\ndata: {payload}\n\n"
                else:
                    yield "event: heartbeat\ndata: {}\n\n"

            last_check = datetime.now(timezone.utc)

    except asyncio.CancelledError:
        logger.info("sse_client_disconnected", search_id=search_id)
    except Exception as e:
        logger.error("sse_error", error=str(e))
        yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"


@router.get("/stream")
async def alerts_stream(search_id: str = Query(...)):
    return StreamingResponse(
        _sse_generator(search_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
