"""
Placd — Database Module (PostgreSQL)
Async PostgreSQL backend via SQLAlchemy 2.0 + asyncpg.

This module provides the public API that the rest of the codebase imports.
All functions delegate to the async PostgreSQL engine defined in db.connection.
"""

import asyncio
import json
import time as _time
import hashlib
import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from db.connection import AsyncSessionLocal, engine
from utils.minhash_lsh import deduplicator
from utils.spam_filter import is_spam
from utils.company_trust import calculate_trust_score, get_company_tier, TRUST_SCORE_WEIGHTS
from utils.job_tagger import tag_job

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _run_async(coro):
    """
    Run an async coroutine from synchronous code.
    Handles the case where an event loop is already running (e.g. inside Celery)
    by creating a new thread-based loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an already-running loop (e.g. FastAPI, Celery with async).
        # Use a new thread to avoid deadlock.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


# ─── Schema Initialization ──────────────────────────────────────────────────

async def _async_init_db() -> None:
    """Ensure PostgreSQL schema exists (tables, indexes, extensions)."""
    from pathlib import Path

    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    async with engine.begin() as conn:
        # Execute schema.sql statements — split on semicolons for individual execution
        for statement in schema_sql.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass  # Ignore "already exists" errors


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    _run_async(_async_init_db())

# ─── Job Persistence ─────────────────────────────────────────────────────────

async def async_save_jobs(jobs: list, source: str = None, company_id: str = None, db_session=None) -> tuple[int, int]:
    """
    Centralized job saving logic.
    1. Spam detection — reject obvious spam.
    2. Trust scoring — compute quality score.
    3. Runs fuzzy deduplication via MinHash LSH.
    4. Upserts jobs to PostgreSQL.
    Returns (inserted_count, updated_count).
    """
    if not jobs:
        return 0, 0

    # Convert objects to dicts if needed
    dict_jobs = []
    for j in jobs:
        if hasattr(j, "model_dump"):
            dict_jobs.append(j.model_dump())
        elif hasattr(j, "dict"):
            dict_jobs.append(j.dict())
        elif hasattr(j, "_mapping"):
            dict_jobs.append(dict(j._mapping))
        elif isinstance(j, dict):
            dict_jobs.append(j)

    original_count = len(dict_jobs)

    # 0. Quality filtering: spam detection + trust scoring
    skipped_spam = 0
    quality_jobs = []
    for job in dict_jobs:
        spam, reason = is_spam(job)
        if spam:
            job["is_spam"] = True
            job["spam_reason"] = reason
            skipped_spam += 1
            logger.debug(f"Skipped spam job: {job.get('title', '?')} | {reason}")
            continue
        
        # Compute trust score
        trust = calculate_trust_score(job)
        # Bonus for passing spam check
        trust += TRUST_SCORE_WEIGHTS["no_spam_signals"]
        job["trust_score"] = trust
        job["company_tier"] = get_company_tier(job.get("company", ""))
        job["is_spam"] = False
        job["spam_reason"] = None

        # Step 3: Tag for filter tabs (FAANG / work_mode / internship)
        tag_job(job)

        quality_jobs.append(job)

    if skipped_spam > 0:
        logger.info(f"Spam filter: {skipped_spam}/{original_count} jobs rejected")

    dict_jobs = quality_jobs
    
    # 1. Fuzzy Deduplication
    unique_jobs = await deduplicator.bulk_deduplicate(dict_jobs)
    filtered_count = len(dict_jobs) - len(unique_jobs)
    
    if filtered_count > 0:
        logger.info(f"Batch dedup: {len(unique_jobs)} unique, {filtered_count} duplicates dropped")

    inserted_count = 0
    updated_count = 0

    # Company upsert query — atomically get/create company and return its id
    company_upsert_query = text("""
        INSERT INTO companies (name, domain, logo_url)
        VALUES (:name, :domain, :logo_url)
        ON CONFLICT (domain) DO UPDATE SET
            name     = COALESCE(EXCLUDED.name, companies.name),
            logo_url = COALESCE(EXCLUDED.logo_url, companies.logo_url)
        RETURNING id
    """)

    query = text("""
        INSERT INTO jobs (
            company_id, external_id, title, description, apply_url, source,
            job_type, location, is_remote, status,
            url_hash, last_verified_at, duplicate_of, freshness_score,
            trust_score, is_spam, spam_reason, company_tier,
            is_faang, is_internship, is_hybrid, work_mode, is_student_eligible,
            company_name, company_logo_url, company_domain
        ) VALUES (
            :company_id, :external_id, :title, :description, :apply_url, :source,
            :job_type, :location, :is_remote, :status,
            :url_hash, :last_verified_at, :duplicate_of, :freshness_score,
            :trust_score, :is_spam, :spam_reason, :company_tier,
            :is_faang, :is_internship, :is_hybrid, :work_mode, :is_student_eligible,
            :company_name, :company_logo_url, :company_domain
        )
        ON CONFLICT (url_hash) DO UPDATE SET
            company_id       = COALESCE(EXCLUDED.company_id, jobs.company_id),
            company_name     = COALESCE(EXCLUDED.company_name, jobs.company_name),
            company_logo_url = COALESCE(EXCLUDED.company_logo_url, jobs.company_logo_url),
            company_domain   = COALESCE(EXCLUDED.company_domain, jobs.company_domain),
            last_verified_at = EXCLUDED.last_verified_at,
            status           = EXCLUDED.status,
            duplicate_of     = COALESCE(EXCLUDED.duplicate_of, jobs.duplicate_of),
            freshness_score  = EXCLUDED.freshness_score,
            trust_score      = GREATEST(EXCLUDED.trust_score, jobs.trust_score),
            is_spam          = EXCLUDED.is_spam,
            spam_reason      = EXCLUDED.spam_reason,
            company_tier     = EXCLUDED.company_tier,
            is_faang         = EXCLUDED.is_faang,
            is_internship    = EXCLUDED.is_internship,
            is_hybrid        = EXCLUDED.is_hybrid,
            work_mode        = EXCLUDED.work_mode,
            is_student_eligible = EXCLUDED.is_student_eligible,
            is_remote        = EXCLUDED.is_remote
        RETURNING id, (xmax = 0) AS inserted
    """)

    async def _do_upsert(session):
        nonlocal inserted_count, updated_count
        for job in dict_jobs:
            url = job.get("apply_url") or job.get("url") or str(uuid.uuid4())
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

            job_status = 'active'
            dup_of = job.get('duplicate_of')
            if dup_of:
                job_status = 'duplicate'

            from utils.freshness import freshness_score
            created_dt = job.get("scraped_at") or datetime.utcnow()
            job_source = source or job.get("source", "unknown")
            f_score = freshness_score(created_dt, created_dt, job_source)

            # --- Company: resolve logo via Clearbit if missing, then upsert ---
            resolved_company_id = company_id or job.get("company_id")
            company_name_raw = job.get("company") or job.get("company_name", "")
            company_domain_raw = job.get("company_domain", "")
            company_logo_raw = job.get("company_logo_url", "") or ""

            # Attempt Clearbit logo if we have a domain but no logo
            if company_domain_raw and not company_logo_raw:
                clean_domain = company_domain_raw.replace("https://", "").replace("http://", "").split("/")[0]
                company_logo_raw = f"https://logo.clearbit.com/{clean_domain}"

            # Upsert company if we have a name + domain
            if company_name_raw and company_domain_raw and not resolved_company_id:
                try:
                    c_result = await session.execute(company_upsert_query, {
                        "name": company_name_raw,
                        "domain": company_domain_raw,
                        "logo_url": company_logo_raw or None,
                    })
                    c_row = c_result.fetchone()
                    if c_row:
                        resolved_company_id = str(c_row.id)
                except Exception as e:
                    logger.debug(f"company_upsert_skip: {e}")

            result = await session.execute(query, {
                "company_id":      resolved_company_id,
                "external_id":     job.get("external_id", ""),
                "title":           job.get("title", "Unknown"),
                "description":     job.get("description", ""),
                "apply_url":       url,
                "source":          job_source,
                "job_type":        job.get("job_type", "full-time"),
                "location":        job.get("location", ""),
                "is_remote":       job.get("is_remote", False),
                "status":          job_status,
                "url_hash":        url_hash,
                "last_verified_at": job.get("scraped_at") or datetime.utcnow(),
                "duplicate_of":    dup_of,
                "freshness_score": f_score,
                "trust_score":     job.get("trust_score", 0),
                "is_spam":         job.get("is_spam", False),
                "spam_reason":     job.get("spam_reason"),
                "company_tier":    job.get("company_tier", 0),
                "is_faang":        job.get("is_faang", False),
                "is_internship":   job.get("is_internship", False),
                "is_hybrid":       job.get("is_hybrid", False),
                "work_mode":       job.get("work_mode", "onsite"),
                "is_student_eligible": job.get("is_student_eligible", False),
                # Denormalized company fields — no join needed at query time
                "company_name":     company_name_raw or None,
                "company_logo_url": company_logo_raw or None,
                "company_domain":   company_domain_raw or None,
            })
            row = result.fetchone()
            if row:
                job['id'] = row.id
                job['freshness_score'] = f_score
                if row.inserted:
                    inserted_count += 1
                else:
                    updated_count += 1

    if db_session:
        await _do_upsert(db_session)
    else:
        async with AsyncSessionLocal() as session:
            await _do_upsert(session)
            await session.commit()

    # Sync to Typesense (fire-and-forget)
    try:
        from search.typesense_sync import typesense_sync
        active_jobs = [j for j in dict_jobs if not j.get('duplicate_of') and 'id' in j]
        if active_jobs:
            await typesense_sync.upsert_batch(active_jobs)
    except Exception as e:
        logger.error(f"typesense_sync_error: {e}")

    return inserted_count, updated_count



# ─── Job Queries ─────────────────────────────────────────────────────────────

async def _async_search_jobs(query: str, page: int = 1, limit: int = 50) -> dict:
    """Full-text search using PostgreSQL ts_vector."""
    offset = (page - 1) * limit

    async with AsyncSessionLocal() as session:
        count_res = await session.execute(
            text("""
                SELECT COUNT(*) FROM jobs
                WHERE to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, ''))
                      @@ websearch_to_tsquery('english', :q)
                  AND status = 'active'
            """),
            {"q": query},
        )
        total = count_res.scalar() or 0

        rows_res = await session.execute(
            text("""
                SELECT * FROM jobs
                WHERE to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, ''))
                      @@ websearch_to_tsquery('english', :q)
                  AND status = 'active'
                ORDER BY ts_rank(
                    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')),
                    websearch_to_tsquery('english', :q)
                ) DESC
                LIMIT :limit OFFSET :offset
            """),
            {"q": query, "limit": limit, "offset": offset},
        )
        rows = rows_res.fetchall()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": [dict(r._mapping) for r in rows],
    }


async def _async_get_all_jobs(
    search: str = "",
    job_type: str = "",
    source: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """Paginated job listing with optional filters."""
    if search and search.strip():
        return await _async_search_jobs(search.strip(), page=page, limit=limit)

    offset = (page - 1) * limit
    where_parts = ["status = 'active'"]
    params: dict = {}

    if job_type:
        if job_type == "internship":
            where_parts.append("job_type = 'internship'")
        elif job_type == "fulltime":
            where_parts.append("job_type = 'fulltime'")
        elif job_type == "remote":
            where_parts.append("is_remote = true")
        else:
            where_parts.append("job_type = :job_type")
            params["job_type"] = job_type

    if source:
        where_parts.append("source = :source")
        params["source"] = source
    if status:
        where_parts[0] = "status = :status"
        params["status"] = status

    where_sql = " AND ".join(where_parts)

    async with AsyncSessionLocal() as session:
        count_res = await session.execute(
            text(f"SELECT COUNT(*) FROM jobs WHERE {where_sql}"), params
        )
        total = count_res.scalar() or 0

        params["limit"] = limit
        params["offset"] = offset
        rows_res = await session.execute(
            text(f"SELECT * FROM jobs WHERE {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params,
        )
        rows = rows_res.fetchall()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": [dict(r._mapping) for r in rows],
    }


def get_all_jobs(
    search: str = "",
    job_type: str = "",
    source: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """Sync wrapper — paginated job listing with optional filters."""
    return _run_async(
        _async_get_all_jobs(search=search, job_type=job_type, source=source, status=status, page=page, limit=limit)
    )


# ─── Stats (cached in-memory, 5 min TTL) ────────────────────────────────────

_stats_cache: dict = {}
_stats_cache_ts: float = 0.0
_STATS_TTL: float = 300.0


async def _async_get_job_stats() -> dict:
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT
                COUNT(*)                                             AS total,
                SUM(CASE WHEN job_type = 'internship' THEN 1 ELSE 0 END) AS internships,
                SUM(CASE WHEN job_type = 'fulltime'   THEN 1 ELSE 0 END) AS fulltime,
                SUM(CASE WHEN is_remote = true         THEN 1 ELSE 0 END) AS remote
            FROM jobs
            WHERE status = 'active'
        """))
        row = res.fetchone()

    return {
        "total": row[0] or 0 if row else 0,
        "internships": row[1] or 0 if row else 0,
        "fulltime": row[2] or 0 if row else 0,
        "remote": row[3] or 0 if row else 0,
    }


def get_job_stats() -> dict:
    """Fast lightweight stats — cached in memory for 5 minutes."""
    global _stats_cache, _stats_cache_ts
    now = _time.time()
    if _stats_cache and (now - _stats_cache_ts) < _STATS_TTL:
        return _stats_cache
    _stats_cache = _run_async(_async_get_job_stats())
    _stats_cache_ts = now
    return _stats_cache


# ─── Scraping State (cursor persistence) ────────────────────────────────────

async def _async_get_scraping_state(source: str) -> dict:
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(
                text("SELECT state_data FROM scraping_state WHERE source = :source"),
                {"source": source},
            )
            row = res.fetchone()
            if row and row[0]:
                return json.loads(row[0])
        except Exception:
            pass
    return {}


async def _async_save_scraping_state(source: str, state: dict) -> None:
    async with AsyncSessionLocal() as session:
        try:
            now_iso = datetime.now().isoformat()
            await session.execute(
                text("""
                    INSERT INTO scraping_state (source, state_data, updated_at)
                    VALUES (:source, :state_data, :updated_at)
                    ON CONFLICT (source) DO UPDATE SET
                        state_data = EXCLUDED.state_data,
                        updated_at = EXCLUDED.updated_at
                """),
                {"source": source, "state_data": json.dumps(state), "updated_at": now_iso},
            )
            await session.commit()
        except Exception:
            pass


def get_scraping_state(source: str) -> dict:
    """Retrieve the last scraping cursor/state for a source."""
    return _run_async(_async_get_scraping_state(source))


def save_scraping_state(source: str, state: dict) -> None:
    """Save the scraping cursor/state for a source."""
    _run_async(_async_save_scraping_state(source, state))


# ─── Main entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("[OK] PostgreSQL database initialized.")
