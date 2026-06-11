import asyncio
from datetime import datetime
import httpx
import structlog
from celery import shared_task
from sqlalchemy import text

# Assuming AsyncSessionLocal is provided by db.connection
from db.connection import AsyncSessionLocal

from utils.url_classifier import is_job_listing_page, is_same_job, normalize_apply_url
from utils.async_utils import run_async
from search.typesense_sync import typesense_sync

from utils.redis import redis_client

logger = structlog.get_logger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; PlacdBot/1.0; +https://placd.in/bot)"

async def _check_url_liveness(client: httpx.AsyncClient, job_id: str, url: str) -> str:
    """
    Perform a HEAD request following redirects.
    Returns the new status: 'active', 'expired', or 'error'/'retry'.
    """
    try:
        # Check cache first
        cache_key = f"liveness:{url}"
        cached_status = await redis_client.get(cache_key)
        if cached_status:
            return cached_status

        # Execute HEAD request
        response = await client.head(url, follow_redirects=True)
        
        if response.status_code == 404:
            status = "expired"
        elif response.status_code in (429, 503):
            status = "retry"
        elif response.status_code == 200:
            final_url = str(response.url)
            
            # If we were redirected to a catch-all board, the job is expired
            if final_url != url and is_job_listing_page(final_url):
                if not is_same_job(url, final_url):
                    status = "expired"
                else:
                    status = "active"
            else:
                status = "active"
        else:
            # Other errors (e.g., 500) we skip to avoid false expirations
            status = "error"
            
        # Cache the result for 4 hours
        if status in ("active", "expired"):
            await redis_client.setex(cache_key, 14400, status)
            
        return status
        
    except httpx.RequestError as e:
        logger.debug("liveness_network_error", job_id=job_id, error=str(e))
        return "error"

async def _verify_new_jobs():
    logger.info("starting_verify_new_jobs")
    
    query = text("""
        SELECT id, apply_url 
        FROM jobs 
        WHERE last_verified_at IS NULL 
          AND created_at > NOW() - INTERVAL '2 hours'
    """)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        jobs = result.fetchall()
        
        if not jobs:
            return
            
        logger.info("verifying_new_jobs", count=len(jobs))
        
        async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": USER_AGENT}) as client:
            for job in jobs:
                status = await _check_url_liveness(client, str(job.id), job.apply_url)
                
                if status == "active":
                    await session.execute(
                        text("UPDATE jobs SET status = 'active', last_verified_at = NOW() WHERE id = :id"),
                        {"id": job.id}
                    )
                elif status == "expired":
                    await session.execute(
                        text("UPDATE jobs SET status = 'expired', expires_at = NOW() WHERE id = :id"),
                        {"id": job.id}
                    )
                    await typesense_sync.delete_job(str(job.id))
                    
        await session.commit()

@shared_task(name="verify_new_jobs_task")
def verify_new_jobs_task():
    """Run within 1 hour of any new job being ingested."""
    run_async(_verify_new_jobs())


async def _daily_liveness_sweep():
    logger.info("starting_daily_liveness_sweep")
    
    query = text("""
        SELECT id, apply_url 
        FROM jobs 
        WHERE status = 'active' 
          AND last_verified_at < NOW() - INTERVAL '23 hours'
        ORDER BY last_verified_at ASC
        LIMIT 5000
    """)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        jobs = result.fetchall()
        
        if not jobs:
            logger.info("no_jobs_for_liveness_sweep")
            return
            
        logger.info("sweeping_active_jobs", count=len(jobs))
        
        semaphore = asyncio.Semaphore(50)
        
        # We will batch updates in chunks of 100
        updates = []
        
        async def _process_job(client: httpx.AsyncClient, job_id: str, url: str):
            async with semaphore:
                return job_id, await _check_url_liveness(client, job_id, url)
                
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            tasks = [_process_job(client, str(job.id), job.apply_url) for job in jobs]
            
            for coro in asyncio.as_completed(tasks):
                job_id, status = await coro
                updates.append((job_id, status))
                
                if len(updates) >= 100:
                    await _apply_liveness_updates(session, updates)
                    updates.clear()
                    
            if updates:
                await _apply_liveness_updates(session, updates)
                
async def _apply_liveness_updates(session, updates):
    for job_id, status in updates:
        if status == "active":
            await session.execute(
                text("UPDATE jobs SET last_verified_at = NOW(), last_active_at = NOW() WHERE id = :id"),
                {"id": job_id}
            )
        elif status == "expired":
            await session.execute(
                text("UPDATE jobs SET status = 'expired', expires_at = NOW() WHERE id = :id"),
                {"id": job_id}
            )
            await typesense_sync.delete_job(str(job_id))
        elif status == "retry":
            # For 429/503 we can rely on celery retry for this specific ID if we wanted,
            # but since this is a batch sweep, we can simply leave last_verified_at alone,
            # and the next sweep (or a targeted retry task) will pick it up.
            # Here we invoke a separate targeted celery task for retry in 1 hour
            # liveness_retry_task.apply_async(args=[job_id], countdown=3600)
            pass
            
    await session.commit()

@shared_task(name="daily_liveness_sweep_task")
def daily_liveness_sweep_task():
    """Run every 24 hours."""
    run_async(_daily_liveness_sweep())


async def _mark_stale_jobs():
    logger.info("starting_mark_stale_jobs")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            UPDATE jobs 
            SET status = 'unverified' 
            WHERE status = 'active' 
              AND last_active_at < NOW() - INTERVAL '7 days'
        """))
        await session.commit()
        logger.info("marked_stale_jobs", count=result.rowcount)

@shared_task(name="mark_stale_jobs_task")
def mark_stale_jobs_task():
    """Run every 6 hours. Mark jobs unverified if not seen recently."""
    run_async(_mark_stale_jobs())


async def _reactivate_reopened_jobs():
    logger.info("starting_reactivate_reopened_jobs")
    
    query = text("""
        SELECT id, apply_url 
        FROM jobs 
        WHERE status = 'expired' 
          AND expires_at < NOW() - INTERVAL '3 days'
    """)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        jobs = result.fetchall()
        
        if not jobs:
            return
            
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            for job in jobs:
                status = await _check_url_liveness(client, str(job.id), job.apply_url)
                
                if status == "active":
                    await session.execute(
                        text("""
                            UPDATE jobs 
                            SET status = 'active', last_verified_at = NOW() 
                            WHERE id = :id
                        """),
                        {"id": job.id}
                    )
                    await session.execute(
                        text("""
                            INSERT INTO sources (job_id, source, source_url, seen_at)
                            VALUES (:job_id, 'reactivation', :source_url, NOW())
                        """),
                        {"job_id": job.id, "source_url": job.apply_url}
                    )
                    logger.info("job_reactivated", job_id=str(job.id))
                    
                    # Optional: Re-fetch job data to upsert into Typesense, or let next scrape handle it.
                    # We will let the next scrape/enrichment handle full Typesense data, 
                    # but we could also do a targeted upsert here if we had all fields.
                    
        await session.commit()

@shared_task(name="reactivate_reopened_jobs_task")
def reactivate_reopened_jobs_task():
    """Some jobs get reposted at the same URL."""
    run_async(_reactivate_reopened_jobs())

async def _update_freshness_scores():
    logger.info("starting_freshness_update")
    from utils.freshness import freshness_score
    
    query = text("""
        SELECT id, created_at, source 
        FROM jobs 
        WHERE status = 'active'
    """)
    
    updates = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        jobs = result.fetchall()
        
        now = datetime.utcnow()
        for job in jobs:
            # updated_at isn't explicitly used currently, use created_at
            score = freshness_score(job.created_at, job.created_at, job.source)
            updates.append({"id": job.id, "freshness_score": score})
            
        if not updates:
            return
            
        # Bulk update freshness_score
        # For huge tables, this might need batching, but we batch by 1000s
        for i in range(0, len(updates), 1000):
            batch = updates[i:i+1000]
            await session.execute(
                text("UPDATE jobs SET freshness_score = :freshness_score WHERE id = :id"),
                batch
            )
        await session.commit()
        logger.info("completed_freshness_update", updated_count=len(updates))
        
        # We also need to update Typesense
        # We can just re-fetch the jobs and batch update them in Typesense
        # or we could do a partial update since we just need to update freshness_score
        try:
            for i in range(0, len(updates), 500):
                batch = updates[i:i+500]
                ts_docs = [{"id": str(u["id"]), "freshness_score": u["freshness_score"]} for u in batch]
                await typesense_sync.upsert_batch(ts_docs, batch_size=500)
        except Exception as e:
            logger.error("typesense_freshness_sync_error", error=str(e))

@shared_task(name="update_freshness_scores_task")
def update_freshness_scores_task():
    """Run nightly to recalculate freshness for all active jobs."""
    run_async(_update_freshness_scores())


async def liveness_background_loop():
    """
    Runs all liveness tasks in a continuous loop for single-process setups 
    (like Render free tier). This replaces the need for Celery Beat.
    """
    logger.info("starting_liveness_background_loop")
    while True:
        try:
            logger.info("running_background_liveness_sweep")
            await _verify_new_jobs()
            await _daily_liveness_sweep()
            await _mark_stale_jobs()
            await _reactivate_reopened_jobs()
            await _update_freshness_scores()
        except Exception as e:
            logger.error("liveness_background_loop_error", error=str(e))
        
        # Sleep for 1 hour before running the sweep again
        await asyncio.sleep(3600)

