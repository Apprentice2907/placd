from fastapi import APIRouter, Query, Request
from typing import Optional, List
import structlog
from search.typesense_sync import typesense_sync
from api.services import get_jobs_api

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v2/jobs")

@router.get("/search")
async def search_jobs_v2(
    request: Request,
    q: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    seniority: Optional[str] = None,
    function: Optional[str] = None,
    skills: Optional[str] = None,  # comma-separated
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    source: Optional[str] = None,
    quality: Optional[str] = Query(None, description="high|verified|all (default=spam-filtered)"),
    filter: Optional[str] = Query(None, description="faang|remote|internship|hybrid"),
    work_mode: Optional[str] = Query(None, description="remote|hybrid|onsite"),
    student_mode: Optional[bool] = None,
    status: str = "active",
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """
    Search jobs with Typesense backend, fallback to PostgreSQL FTS on failure.
    """
    # Determine trust_score threshold based on quality param
    quality_thresholds = {
        "high": 80,       # Tier 1 companies + complete data
        "verified": 50,   # Known companies, complete data
        "all": 0,         # Everything (power users)
    }
    trust_min = quality_thresholds.get(quality or "", 30)  # Default: spam filtered

    # Resolve tab filter → boolean column names
    VALID_FILTERS = {"faang", "remote", "internship", "hybrid"}
    VALID_WORK_MODES = {"remote", "hybrid", "onsite"}
    active_filter = filter if filter in VALID_FILTERS else None
    active_work_mode = work_mode if work_mode in VALID_WORK_MODES else None

    filters = {
        "status": status,
    }
    if remote is not None: filters["is_remote"] = remote
    if seniority: filters["seniority"] = seniority
    if function: filters["function"] = function
    # Tab filter → Typesense filter fields
    if active_filter == "faang":       filters["is_faang"] = True
    if active_filter == "remote":      filters["is_remote"] = True
    if active_filter == "internship":  filters["is_internship"] = True
    if active_filter == "hybrid":      filters["is_hybrid"] = True
    if active_work_mode:               filters["work_mode"] = active_work_mode
    if student_mode:                   filters["is_student_eligible"] = True
    
    # Typesense query
    try:
        ts_result = await typesense_sync.search(query=q, filters=filters, page=page, per_page=per_page)
        
        jobs = []
        for hit in ts_result.get("hits", []):
            doc = hit.get("document", {})
            # Apply trust_score filter on Typesense results
            if doc.get("trust_score", 0) >= trust_min:
                jobs.append(doc)
            
        facets = {}
        for facet in ts_result.get("facet_counts", []):
            field_name = facet.get("field_name")
            counts = {count.get("value"): count.get("count") for count in facet.get("counts", [])}
            facets[field_name] = counts
            
        return {
            "jobs": jobs,
            "total": ts_result.get("found", 0),
            "page": page,
            "facets": facets,
            "search_backend": "typesense",
            "quality_filter": quality or "default",
        }
    except Exception as e:
        logger.error("typesense_search_failed", error=str(e), fallback="postgres")
        # Fall back to PostgreSQL FTS via services.py — with trust filter
        from db.connection import AsyncSessionLocal
        from sqlalchemy import text as sa_text

        where_parts = ["status = 'active'", "is_spam = FALSE", f"trust_score >= {trust_min}"]
        params = {"limit": per_page, "offset": (page - 1) * per_page}

        if q:
            where_parts.append("(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')) @@ websearch_to_tsquery('english', :q))")
            params["q"] = q
        if remote:
            where_parts.append("is_remote = true")
        if location:
            where_parts.append("location ILIKE :loc")
            params["loc"] = f"%{location}%"
        # Tab filter → Postgres boolean columns
        if active_filter == "faang":      where_parts.append("is_faang = TRUE")
        if active_filter == "remote":     where_parts.append("is_remote = TRUE")
        if active_filter == "internship": where_parts.append("is_internship = TRUE")
        if active_filter == "hybrid":     where_parts.append("is_hybrid = TRUE")
        if active_work_mode:
            where_parts.append("work_mode = :work_mode")
            params["work_mode"] = active_work_mode
        if student_mode:
            where_parts.append("is_student_eligible = TRUE")

        where_sql = " AND ".join(where_parts)
        
        async with AsyncSessionLocal() as session:
            count_res = await session.execute(sa_text(f"SELECT COUNT(*) FROM jobs WHERE {where_sql}"), params)
            total = count_res.scalar() or 0
            rows_res = await session.execute(
                sa_text(f"SELECT * FROM jobs WHERE {where_sql} ORDER BY trust_score DESC, created_at DESC LIMIT :limit OFFSET :offset"),
                params
            )
            rows = rows_res.fetchall()
        
        return {
            "jobs": [dict(r._mapping) for r in rows],
            "total": total,
            "page": page,
            "facets": {},
            "search_backend": "postgres",
            "quality_filter": quality or "default",
        }


@router.get("/featured")
async def featured_jobs(request: Request):
    """
    Returns top 20 jobs by trust_score from Tier 1 companies.
    Cached in Redis for 30 minutes.
    """
    import json
    import redis.asyncio as aioredis
    import os
    
    REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    
    cache_key = "api:jobs:featured"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            await redis_client.aclose()
            return json.loads(cached)
    except Exception:
        pass

    from db.connection import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    async with AsyncSessionLocal() as session:
        res = await session.execute(sa_text("""
            SELECT * FROM jobs 
            WHERE status = 'active' AND is_spam = FALSE AND trust_score >= 80
            ORDER BY trust_score DESC, created_at DESC 
            LIMIT 20
        """))
        rows = res.fetchall()

    jobs_list = []
    for r in rows:
        d = dict(r._mapping)
        if 'created_at' in d and d['created_at']:
            d['created_at'] = d['created_at'].isoformat()
        if 'description_embedding' in d:
            del d['description_embedding']
        jobs_list.append(d)

    data = {"jobs": jobs_list, "total": len(jobs_list)}
    
    try:
        await redis_client.setex(cache_key, 1800, json.dumps(data))  # 30 min cache
    except Exception:
        pass
    
    try:
        await redis_client.aclose()
    except Exception:
        pass
        
    return data
