import json
import hashlib
import time
import os
from typing import List, Optional
from datetime import datetime
import structlog
from fastapi import FastAPI, Request, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, UUID4

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy import text
from db.connection import AsyncSessionLocal, engine
import redis.asyncio as redis

# ── Real Redis Client ────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# ── Celery task import (graceful) ────────────────────────────────────────────
try:
    from workers.liveness import verify_new_jobs_task as _verify_task
except ImportError:
    _verify_task = None


def compute_embedding(text_input):
    """Placeholder — will be implemented with Gemini embeddings."""
    return []


import logging
logger = structlog.get_logger(__name__)

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Placd API", version="1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

from api.routers import search
from api.routers import alerts
from api.routers import recommendations
app.include_router(search.router)
app.include_router(alerts.router)
app.include_router(recommendations.router)

# --- Startup / Shutdown ---

@app.on_event("startup")
async def startup_event():
    """Verify env vars, PostgreSQL, pgvector, and Redis connectivity on boot."""
    from utils.startup_check import run_startup_checks
    results = await run_startup_checks()
    logger.info("startup_complete", checks=results)


@app.on_event("shutdown")
async def shutdown_event():
    from db.connection import close_db_connection
    await close_db_connection()
    await redis_client.aclose()


# --- Schemas ---
class ReportRequest(BaseModel):
    reason: str

class JobStatusRequest(BaseModel):
    status: str


# --- Endpoints ---

@app.get("/api/jobs")
@limiter.limit("100/minute")
async def get_paginated_jobs(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = "",
    type: str = "",
    source: Optional[str] = None,
    status: Optional[str] = "active"
):
    """Paginated jobs endpoint with PostgreSQL full-text search."""
    from db.database import _async_get_all_jobs
    return await _async_get_all_jobs(
        search=search,
        job_type=type,
        source=source,
        status=status,
        page=page,
        limit=limit
    )

@app.get("/api/jobs/search")
@limiter.limit("100/minute")
async def search_jobs(
    request: Request,
    q: Optional[str] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    category: Optional[str] = None,
    company_id: Optional[str] = None,
    location: Optional[str] = None,
    experience_level: Optional[str] = None,
    salary_min: Optional[int] = None,
    tags: Optional[List[str]] = Query(None),
    status: str = "active",
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    sort: str = "newest"
):
    """Dynamic full-text search over jobs with Redis caching."""
    # Build cache key
    params = request.query_params._dict.copy()
    cache_str = json.dumps(params, sort_keys=True)
    cache_key = f"api:jobs:search:{hashlib.md5(cache_str.encode()).hexdigest()}"

    try:
        cached_res = await redis_client.get(cache_key)
        if cached_res:
            return json.loads(cached_res)
    except Exception:
        pass

    where_clauses = ["jobs.status = :status"]
    bind_params = {"status": status}

    if q:
        where_clauses.append("(to_tsvector('english', jobs.title || ' ' || COALESCE(jobs.description, '')) @@ websearch_to_tsquery('english', :q))")
        bind_params["q"] = q

    if job_type:
        where_clauses.append("jobs.job_type = :job_type")
        bind_params["job_type"] = job_type

    if is_remote is not None:
        where_clauses.append("jobs.is_remote = :is_remote")
        bind_params["is_remote"] = is_remote

    if category:
        where_clauses.append(":category = ANY(jobs.tags)")
        bind_params["category"] = category

    if company_id:
        where_clauses.append("jobs.company_id = :company_id")
        bind_params["company_id"] = company_id

    if location:
        where_clauses.append("jobs.location ILIKE :location")
        bind_params["location"] = f"%{location}%"

    if experience_level:
        where_clauses.append("jobs.experience_level = :experience_level")
        bind_params["experience_level"] = experience_level

    if salary_min:
        where_clauses.append("jobs.salary_min >= :salary_min")
        bind_params["salary_min"] = salary_min

    if tags:
        where_clauses.append("jobs.tags && string_to_array(:tags_str, ',')")
        bind_params["tags_str"] = ",".join(tags)

    where_sql = " AND ".join(where_clauses)

    order_sql = "ORDER BY jobs.created_at DESC"
    if sort == "oldest":
        order_sql = "ORDER BY jobs.created_at ASC"
    elif sort == "relevance" and q:
        order_sql = "ORDER BY ts_rank(to_tsvector('english', jobs.title || ' ' || COALESCE(jobs.description, '')), websearch_to_tsquery('english', :q)) DESC"

    offset = (page - 1) * per_page
    bind_params["limit"] = per_page
    bind_params["offset"] = offset

    count_sql = f"SELECT COUNT(1) FROM jobs WHERE {where_sql}"
    data_sql = f"""
        SELECT jobs.id, jobs.title, companies.name AS company_name, companies.logo_url AS c_logo, jobs.location, jobs.job_type, jobs.is_remote, jobs.apply_url, jobs.created_at, jobs.categories, jobs.tags, jobs.salary_min, jobs.salary_max, jobs.salary_currency
        FROM jobs 
        LEFT JOIN companies ON jobs.company_id = companies.id
        WHERE {where_sql} 
        {order_sql} 
        LIMIT :limit OFFSET :offset
    """

    async with AsyncSessionLocal() as session:
        count_res = await session.execute(text(count_sql), bind_params)
        total = count_res.scalar()

        data_res = await session.execute(text(data_sql), bind_params)
        rows = data_res.fetchall()

    jobs_data = [dict(r._mapping) for r in rows]
    for j in jobs_data:
        if 'id' in j and j['id']:
            j['id'] = str(j['id'])
        if 'created_at' in j and j['created_at']:
            j['created_at'] = j['created_at'].isoformat()

    response_data = {
        "jobs": jobs_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (page * per_page) < total
    }

    try:
        await redis_client.setex(cache_key, 300, json.dumps(response_data))
    except Exception:
        pass
    return response_data

@app.get("/api/jobs/{job_id}")
@limiter.limit("100/minute")
async def get_job(request: Request, job_id: str):
    """Get full job details including similar jobs and keywords."""
    async with AsyncSessionLocal() as session:
        # Fetch Job and Company
        job_sql = """
            SELECT j.*, c.name as c_name, c.logo_url as c_logo, c.ats_type as c_ats
            FROM jobs j
            LEFT JOIN companies c ON j.company_id = c.id
            WHERE j.id = :id
        """
        job_res = await session.execute(text(job_sql), {"id": job_id})
        job = job_res.fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job_dict = dict(job._mapping)
        if 'created_at' in job_dict and job_dict['created_at']:
            job_dict['created_at'] = job_dict['created_at'].isoformat()
        if 'last_verified_at' in job_dict and job_dict['last_verified_at']:
            job_dict['last_verified_at'] = job_dict['last_verified_at'].isoformat()
        if 'description_embedding' in job_dict:
            del job_dict['description_embedding']

        keywords = []

        # Fetch Similar Jobs (pgvector)
        similar_jobs = []
        if job.description_embedding:
            sim_sql = """
                SELECT id, title, location
                FROM jobs
                WHERE id != :id AND status = 'active' AND description_embedding IS NOT NULL
                ORDER BY description_embedding <=> :embedding
                LIMIT 5
            """
            sim_res = await session.execute(text(sim_sql), {"id": job_id, "embedding": job.description_embedding})
            similar_jobs = [dict(r._mapping) for r in sim_res.fetchall()]

        return {
            "job": job_dict,
            "keywords": keywords,
            "similar_jobs": similar_jobs
        }

@app.get("/api/companies/search")
@limiter.limit("100/minute")
async def search_companies(
    request: Request,
    q: Optional[str] = None,
    ats_type: Optional[str] = None,
    size_tier: Optional[str] = None,
    country: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Search companies and return open jobs count."""
    where_clauses = ["1=1"]
    bind_params = {}

    if q:
        where_clauses.append("c.name ILIKE :q")
        bind_params["q"] = f"%{q}%"
    if ats_type:
        where_clauses.append("c.ats_type = :ats_type")
        bind_params["ats_type"] = ats_type
    if size_tier:
        where_clauses.append("c.size_tier = :size_tier")
        bind_params["size_tier"] = size_tier
    if country:
        where_clauses.append("c.country = :country")
        bind_params["country"] = country

    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * per_page
    bind_params["limit"] = per_page
    bind_params["offset"] = offset

    query_sql = f"""
        SELECT c.*, 
               (SELECT COUNT(1) FROM jobs j WHERE j.company_id = c.id AND j.status = 'active') as open_jobs_count
        FROM companies c
        WHERE {where_sql}
        ORDER BY open_jobs_count DESC, c.name ASC
        LIMIT :limit OFFSET :offset
    """

    async with AsyncSessionLocal() as session:
        res = await session.execute(text(query_sql), bind_params)
        companies = [dict(r._mapping) for r in res.fetchall()]

    return {"companies": companies, "page": page, "per_page": per_page}

@app.get("/api/stats")
@limiter.limit("100/minute")
async def get_stats(request: Request):
    """System statistics from PostgreSQL."""
    cache_key = "api:stats"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT COUNT(1) FROM jobs WHERE status = 'active'"))
        total_jobs = res.scalar()
        res = await session.execute(text("SELECT COUNT(1) FROM companies"))
        total_companies = res.scalar()
        res = await session.execute(text("SELECT job_type, COUNT(1) FROM jobs WHERE status = 'active' GROUP BY job_type"))
        jobs_by_type = {row[0] or "unknown": row[1] for row in res.fetchall()}
        res = await session.execute(text("SELECT source, COUNT(1) FROM jobs WHERE status = 'active' GROUP BY source"))
        jobs_by_source = {row[0] or "unknown": row[1] for row in res.fetchall()}
        res = await session.execute(text("SELECT COUNT(1) FROM jobs WHERE status = 'active' AND created_at > NOW() - INTERVAL '1 day'"))
        new_jobs_today = res.scalar()
        res = await session.execute(text("SELECT COUNT(1) FROM jobs WHERE status = 'active' AND created_at > NOW() - INTERVAL '7 days'"))
        new_jobs_this_week = res.scalar()
        res = await session.execute(text("SELECT COUNT(1) FROM jobs WHERE status = 'active' AND last_verified_at > NOW() - INTERVAL '24 hours'"))
        fresh = res.scalar()
        freshness_rate = round((fresh / total_jobs * 100), 2) if total_jobs and total_jobs > 0 else 0.0
        res = await session.execute(text("""
            SELECT c.name, COUNT(j.id) as count
            FROM companies c JOIN jobs j ON c.id = j.company_id
            WHERE j.status = 'active'
            GROUP BY c.name ORDER BY count DESC LIMIT 10
        """))
        top_companies = [{"name": r[0], "count": r[1]} for r in res.fetchall()]

    data = {
        "total_jobs": total_jobs, "total_companies": total_companies,
        "jobs_by_type": jobs_by_type, "jobs_by_source": jobs_by_source,
        "new_jobs_today": new_jobs_today, "new_jobs_this_week": new_jobs_this_week,
        "freshness_rate": freshness_rate, "top_companies": top_companies
    }

    try:
        await redis_client.setex(cache_key, 300, json.dumps(data))
    except Exception:
        pass
    return data


@app.get("/api/stats/quick")
@limiter.limit("200/minute")
async def get_stats_quick(request: Request):
    """Quick stats from PostgreSQL with caching."""
    from db.database import _async_get_job_stats
    return await _async_get_job_stats()


@app.get("/api/quality-report")
@limiter.limit("50/minute")
async def get_quality_report_endpoint(request: Request):
    """PostgreSQL-backed quality report for job scraper with 5 min cache."""
    cache_key = "api:quality_report"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT 
              COUNT(*) as total_jobs,
              source,
              COUNT(*) as count_per_source
            FROM jobs
            WHERE status = 'active'
            GROUP BY source
        """))
        rows = [dict(r._mapping) for r in res.fetchall()]

    try:
        await redis_client.setex(cache_key, 300, json.dumps(rows))
    except Exception:
        pass
    return rows

@app.get("/api/sources")
@limiter.limit("50/minute")
async def get_sources_endpoint(request: Request):
    """Returns a list of all sources and their job counts from PostgreSQL."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("SELECT source, COUNT(*) as count FROM jobs WHERE status = 'active' GROUP BY source ORDER BY count DESC")
        )
        return [dict(r._mapping) for r in res.fetchall()]


@app.get("/api/jobs/semantic-search")
@limiter.limit("100/minute")
async def semantic_search(request: Request, query: str = Query(...), limit: int = Query(10, le=50)):
    """Search jobs by semantic similarity using pgvector."""
    cache_key = f"api:semantic:{hashlib.md5(query.encode()).hexdigest()}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    embedding = compute_embedding(query)
    if not embedding:
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

    embedding_str = f"[{','.join(map(str, embedding))}]"

    search_sql = """
        SELECT jobs.id, jobs.title, companies.name AS company_name, companies.logo_url AS c_logo, jobs.location, jobs.apply_url,
               (jobs.description_embedding <=> :embedding::vector) as distance
        FROM jobs
        LEFT JOIN companies ON jobs.company_id = companies.id
        WHERE jobs.status = 'active' AND jobs.description_embedding IS NOT NULL
        ORDER BY description_embedding <=> :embedding::vector
        LIMIT :limit
    """

    async with AsyncSessionLocal() as session:
        res = await session.execute(text(search_sql), {"embedding": embedding_str, "limit": limit})
        jobs = [dict(r._mapping) for r in res.fetchall()]

    response_data = {"query": query, "results": jobs}
    try:
        await redis_client.setex(cache_key, 3600, json.dumps(response_data))
    except Exception:
        pass
    return response_data


@app.post("/api/jobs/{job_id}/report")
@limiter.limit("10/minute")
async def report_job(request: Request, job_id: str, payload: ReportRequest):
    """Report a dead link to queue immediate verification."""
    logger.info("job_reported", job_id=job_id, reason=payload.reason)
    if _verify_task:
        try:
            _verify_task.apply_async()
        except Exception:
            pass
    return {"message": "Thanks, we will verify this link"}


@app.patch("/api/jobs/{job_id}/status")
@limiter.limit("50/minute")
async def update_job_status(request: Request, job_id: str, payload: JobStatusRequest):
    """Update job status (e.g. for bookmarking/shortlisting) via PostgreSQL."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT id FROM jobs WHERE id = :id"), {"id": job_id})
        if not res.fetchone():
            raise HTTPException(status_code=404, detail="Job not found")

        await session.execute(
            text("UPDATE jobs SET status = :status WHERE id = :id"),
            {"status": payload.status, "id": job_id},
        )
        await session.commit()

    return {"success": True, "job_id": job_id, "status": payload.status}
