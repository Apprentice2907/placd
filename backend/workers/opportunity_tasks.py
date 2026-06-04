import logging
from datetime import datetime, timedelta
from sqlalchemy import text

from workers.celery_config import app as celery_app
from utils.async_utils import run_async
from scrapers.opportunities.opportunities_corners import OpportunitiesCornersScraper, OPPORTUNITIES_CORNERS_CATEGORIES
from scrapers.opportunities.opportunities_circle import OpportunitiesCircleScraper, OPPORTUNITIES_CIRCLE_CATEGORIES
from db.connection import AsyncSessionLocal
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(name='crawl_opportunities_corners')
def crawl_opportunities_corners_task():
    async def _run():
        scraper = OpportunitiesCornersScraper()
        try:
            for category, opp_type in OPPORTUNITIES_CORNERS_CATEGORIES.items():
                records = await scraper.crawl_category(category, opportunity_type=opp_type)
                await scraper.upsert_opportunities(records)
        finally:
            await scraper._close()
            
    run_async(_run())

@celery_app.task(name='crawl_opportunities_circle')
def crawl_opportunities_circle_task():
    async def _run():
        scraper = OpportunitiesCircleScraper()
        try:
            for category, opp_type in OPPORTUNITIES_CIRCLE_CATEGORIES.items():
                records = await scraper.crawl_category(category, opportunity_type=opp_type)
                await scraper.upsert_opportunities(records)
        finally:
            await scraper._close()
            
    run_async(_run())

@celery_app.task(name='crawl_all_opportunities')
def crawl_all_opportunities_task():
    # Runs both sequentially
    logger.info("Starting crawl_all_opportunities_task")
    crawl_opportunities_corners_task()
    crawl_opportunities_circle_task()
    logger.info("Completed crawl_all_opportunities_task")

@celery_app.task(name='sweep_expired_opportunities')
def sweep_expired_opportunities_task():
    async def _run():
        logger.info("Sweeping expired opportunities...")
        async with AsyncSessionLocal() as session:
            # Mark expired based on deadline
            # If deadline is strictly in the past (before today)
            query_expired = text("""
                UPDATE opportunities
                SET status = 'expired'
                WHERE status = 'active'
                  AND deadline IS NOT NULL
                  AND deadline < CURRENT_DATE
            """)
            result = await session.execute(query_expired)
            expired_count = result.rowcount
            await session.commit()
            
            logger.info(f"Marked {expired_count} opportunities as expired based on deadline.")
            
            # HEAD check for 404s for jobs older than 7 days that are still active
            # For simplicity in this background task, we just do a DB update on old unverified.
            # "HEAD-check URLs older than 7 days: 404 -> expired"
            # This requires fetching URLs, which can take a long time, so we batch it.
            query_old = text("""
                SELECT id, source_url FROM opportunities
                WHERE status = 'active'
                  AND first_seen_at < NOW() - INTERVAL '7 days'
                LIMIT 100
            """)
            res = await session.execute(query_old)
            old_opps = res.fetchall()
            
            if old_opps:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    expired_ids = []
                    for opp_id, url in old_opps:
                        try:
                            # Avoid ratelimits
                            await asyncio.sleep(0.5)
                            resp = await client.head(url)
                            if resp.status_code == 404:
                                expired_ids.append(opp_id)
                        except Exception:
                            # Timeout or other error doesn't necessarily mean expired, but we can treat 404 strictly
                            pass
                            
                    if expired_ids:
                        query_mark = text("""
                            UPDATE opportunities
                            SET status = 'expired'
                            WHERE id = ANY(:ids)
                        """)
                        await session.execute(query_mark, {"ids": expired_ids})
                        await session.commit()
                        logger.info(f"Marked {len(expired_ids)} older opportunities as expired via 404 HEAD check.")
                        
    run_async(_run())
