from fastapi import APIRouter, Query, Request
from typing import Optional
import structlog
from search.typesense_sync import typesense_sync

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v2/jobs")


def _map_job_row(r) -> dict:
    """Convert a DB row to a clean job dict, removing heavy/internal fields."""
    d = dict(r._mapping)
    # Remove the heavy embedding vector
    d.pop("description_embedding", None)
    d.pop("search_vector", None)
    # Serialize datetimes
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


@router.get("/search")
async def search_jobs_v2(
    request: Request,
    q: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    seniority: Optional[str] = None,
    function: Optional[str] = None,
    skills: Optional[str] = None,  # comma-separated
    job_type: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    source: Optional[str] = None,
    quality: Optional[str] = Query(None, description="high|verified|all (default=spam-filtered)"),
    filter: Optional[str] = Query(None, description="faang|remote|internship|hybrid"),
    work_mode: Optional[str] = Query(None, description="remote|hybrid|onsite"),
    student_mode: Optional[bool] = None,
    status: str = "active",
    sort: Optional[str] = Query("newest", description="newest|oldest|relevance"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """
    Search jobs using the stored GIN tsvector index for fast FTS.
    Falls back gracefully. Supports full filtering, sorting, and pagination.
    """
    quality_thresholds = {
        "high": 80,
        "verified": 50,
        "all": 0,
    }
    trust_min = quality_thresholds.get(quality or "", 30)

    VALID_FILTERS = {"faang", "remote", "internship", "hybrid"}
    VALID_WORK_MODES = {"remote", "hybrid", "onsite"}
    active_filter = filter if filter in VALID_FILTERS else None
    active_work_mode = work_mode if work_mode in VALID_WORK_MODES else None

    # --- Always go straight to PostgreSQL (Typesense disabled) ---
    try:
        ts_result = await typesense_sync.search(query=q, filters={}, page=page, per_page=per_page)
        # If we somehow get here with Typesense enabled, handle it
        jobs = [hit.get("document", {}) for hit in ts_result.get("hits", [])
                if hit.get("document", {}).get("trust_score", 0) >= trust_min]
        total = ts_result.get("found", 0)
        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": (page * per_page) < total,
            "facets": {},
            "search_backend": "typesense",
        }
    except Exception:
        pass  # Fall through to Postgres

    from db.connection import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    where_parts = [f"status = '{status}'", "is_spam = FALSE", f"trust_score >= {trust_min}"]
    params: dict = {"limit": per_page, "offset": (page - 1) * per_page}

    # --- Full-text search using GIN index (fast!) ---
    if q and q.strip():
        where_parts.append("search_vector @@ websearch_to_tsquery('english', :q)")
        params["q"] = q.strip()

    if remote is not None:
        where_parts.append("is_remote = :is_remote")
        params["is_remote"] = remote

    if location:
        where_parts.append("location ILIKE :loc")
        params["loc"] = f"%{location}%"

    if job_type:
        types = [t.strip() for t in job_type.split(',')]
        conditions = []
        regular_types = []
        for i, t in enumerate(types):
            if t.lower() == "internship":
                conditions.append("is_internship = TRUE")
            else:
                regular_types.append(t)
        
        if regular_types:
            placeholders = []
            for i, rt in enumerate(regular_types):
                placeholders.append(f"LOWER(job_type) = LOWER(:job_type_{i})")
                params[f"job_type_{i}"] = rt
            conditions.append("(" + " OR ".join(placeholders) + ")")
            
        if conditions:
            where_parts.append("(" + " OR ".join(conditions) + ")")

    if seniority:
        where_parts.append("experience_level ILIKE :seniority")
        params["seniority"] = f"%{seniority}%"

    if salary_min is not None:
        # The job's maximum salary must be at least the user's minimum requested
        where_parts.append("(salary_max IS NULL OR salary_max >= :user_salary_min)")
        params["user_salary_min"] = salary_min

    if salary_max is not None:
        # The job's minimum salary must be at most the user's maximum requested
        where_parts.append("(salary_min IS NULL OR salary_min <= :user_salary_max)")
        params["user_salary_max"] = salary_max

    if source:
        where_parts.append("source = :source")
        params["source"] = source

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

    # Order by relevance (ts_rank) when searching, else trust_score + recency
    if q and q.strip() and sort == "newest":
        order_sql = "ORDER BY ts_rank(search_vector, websearch_to_tsquery('english', :q)) DESC, created_at DESC"
    elif sort == "oldest":
        order_sql = "ORDER BY created_at ASC"
    else:
        order_sql = "ORDER BY trust_score DESC, created_at DESC"

    async with AsyncSessionLocal() as session:
        count_res = await session.execute(
            sa_text(f"SELECT COUNT(*) FROM jobs WHERE {where_sql}"),
            params
        )
        total = count_res.scalar() or 0

        rows_res = await session.execute(
            sa_text(
                f"""
                SELECT id, company_id, external_id, title,
                       company_name, company_logo_url, company_domain,
                       location, job_type, is_remote, is_student_eligible,
                       apply_url, created_at, tags, categories,
                       salary_min, salary_max, salary_currency,
                       experience_level, source, status, trust_score,
                       is_faang, is_internship, is_hybrid, work_mode,
                       freshness_score
                FROM jobs WHERE {where_sql}
                {order_sql}
                LIMIT :limit OFFSET :offset
                """
            ),
            params
        )
        rows = rows_res.fetchall()

    return {
        "jobs": [_map_job_row(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (page * per_page) < total,
        "facets": {},
        "search_backend": "postgres_gin",
    }


@router.get("/facets")
async def get_facets():
    """
    Returns aggregated filter counts for the sidebar.
    Cached-friendly — long staleTime on frontend (5 min).
    """
    from db.connection import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    async with AsyncSessionLocal() as session:
        res = await session.execute(sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE LOWER(job_type) = 'fulltime') AS fulltime,
                COUNT(*) FILTER (WHERE LOWER(job_type) = 'parttime') AS parttime,
                COUNT(*) FILTER (WHERE is_remote = TRUE OR LOWER(job_type) = 'remote') AS remote,
                COUNT(*) FILTER (WHERE is_internship = TRUE OR LOWER(job_type) = 'internship') AS internship,

                COUNT(*) FILTER (WHERE experience_level ILIKE '%intern%' OR experience_level ILIKE '%student%') AS student_level,
                COUNT(*) FILTER (WHERE experience_level ILIKE '%entry%' OR experience_level ILIKE '%junior%') AS entry_level,
                COUNT(*) FILTER (WHERE experience_level ILIKE '%mid%' OR experience_level ILIKE '%middle%') AS mid_level,
                COUNT(*) FILTER (WHERE experience_level ILIKE '%senior%' OR experience_level ILIKE '%sr%') AS senior_level,
                COUNT(*) FILTER (WHERE experience_level ILIKE '%director%' OR experience_level ILIKE '%lead%') AS director_level,
                COUNT(*) FILTER (WHERE experience_level ILIKE '%vp%' OR experience_level ILIKE '%vice%' OR experience_level ILIKE '%c-level%') AS vp_level,

                COUNT(*) AS total
            FROM jobs
            WHERE status = 'active' AND is_spam = FALSE
        """))
        row = dict(res.fetchone()._mapping)

    return {
        "employment_type": {
            "full_time": row["fulltime"],
            "part_time": row["parttime"],
            "remote": row["remote"],
            "internship": row["internship"],
        },
        "seniority": {
            "student": row["student_level"],
            "entry": row["entry_level"],
            "mid": row["mid_level"],
            "senior": row["senior_level"],
            "director": row["director_level"],
            "vp": row["vp_level"],
        },
        "total": row["total"],
    }


@router.get("/featured")
async def featured_jobs(request: Request):
    """
    Returns top 20 jobs by trust_score from Tier 1 companies.
    """
    from db.connection import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    async with AsyncSessionLocal() as session:
        res = await session.execute(sa_text("""
            SELECT id, title, company_name, company_logo_url, location,
                   job_type, is_remote, apply_url, created_at, source,
                   trust_score, experience_level
            FROM jobs
            WHERE status = 'active' AND is_spam = FALSE AND trust_score >= 80
            ORDER BY trust_score DESC, created_at DESC
            LIMIT 20
        """))
        rows = res.fetchall()

    return {"jobs": [_map_job_row(r) for r in rows], "total": len(rows)}
