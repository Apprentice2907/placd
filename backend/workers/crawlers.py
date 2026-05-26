import asyncio
import structlog
from celery import Celery, shared_task
from sqlalchemy import text
from db.connection import AsyncSessionLocal
import os

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery(
    "placd_crawlers",
    broker=redis_url,
    backend=redis_url,
    include=['workers.crawlers', 'workers.enricher', 'workers.liveness', 'workers.opportunity_tasks', 'workers.playwright_tasks']
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Import crawlers
from scrapers.ats.greenhouse import GreenhouseCrawler
from scrapers.ats.lever import LeverCrawler
from scrapers.ats.ashby import AshbyCrawler
from scrapers.ats.workable import WorkableCrawler

logger = structlog.get_logger(__name__)

def get_crawler(ats_type: str):
    """Factory to return the appropriate crawler instance."""
    if ats_type == "greenhouse":
        return GreenhouseCrawler()
    elif ats_type == "lever":
        return LeverCrawler()
    elif ats_type == "ashby":
        return AshbyCrawler()
    elif ats_type == "workable":
        return WorkableCrawler()
    return None

async def _crawl_company_async(company_id: str):
    """Async implementation of the crawl company task."""
    logger.info("starting_company_crawl", company_id=company_id)
    
    async with AsyncSessionLocal() as session:
        # Load company
        result = await session.execute(
            text("SELECT id, name, ats_type, ats_slug FROM companies WHERE id = :id"),
            {"id": company_id}
        )
        company = result.fetchone()
        
        if not company:
            logger.error("company_not_found", company_id=company_id)
            return
            
        ats_type = company.ats_type
        ats_slug = company.ats_slug
        
        crawler = get_crawler(ats_type)
        if not crawler:
            logger.warning("unsupported_ats_type", ats_type=ats_type, company_id=company_id)
            return
            
        try:
            # Crawl
            jobs = await crawler.crawl_company(ats_slug)
            
            # Save
            inserted, updated = await crawler.save_jobs(jobs, session, company_id=company_id)
            
            # Update company last_crawled_at
            await session.execute(
                text("""
                    UPDATE companies 
                    SET last_crawled_at = NOW(), 
                        crawl_status = 'active' 
                    WHERE id = :id
                """),
                {"id": company_id}
            )
            
            # Insert crawl log
            await session.execute(
                text("""
                    INSERT INTO crawl_log (company_id, source, jobs_found, jobs_new, crawled_at)
                    VALUES (:company_id, :source, :jobs_found, :jobs_new, NOW())
                """),
                {
                    "company_id": company_id,
                    "source": ats_type,
                    "jobs_found": len(jobs),
                    "jobs_new": inserted
                }
            )
            
            await session.commit()
            
            logger.info("crawl_company_success", 
                        company_id=company_id, 
                        jobs_found=len(jobs), 
                        inserted=inserted, 
                        updated=updated)
                        
        except Exception as e:
            logger.error("crawl_company_failed", company_id=company_id, error=str(e))
            await session.rollback()
            raise e

@shared_task(name="crawl_company_task", rate_limit='100/m', max_retries=3, default_retry_delay=60)
def crawl_company_task(company_id: str):
    """Celery task to crawl a single company."""
    asyncio.run(_crawl_company_async(company_id))

async def _crawl_all_companies_async():
    """Async implementation to fetch companies and dispatch tasks."""
    logger.info("starting_crawl_all_companies")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id FROM companies 
                WHERE crawl_status = 'active' 
                  AND (last_crawled_at IS NULL OR last_crawled_at < NOW() - INTERVAL '6 hours')
                ORDER BY crawl_priority ASC
            """)
        )
        companies_to_crawl = result.fetchall()
        
    for index, row in enumerate(companies_to_crawl):
        # Stagger dispatch to prevent overwhelming the queues
        delay = index * 2  # 2 seconds between each dispatch
        crawl_company_task.apply_async(args=[str(row.id)], countdown=delay)
        
    logger.info("dispatched_crawl_tasks", count=len(companies_to_crawl))

@shared_task(name="crawl_all_companies_task")
def crawl_all_companies_task():
    """Celery task to find companies due for crawling and dispatch them."""
    asyncio.run(_crawl_all_companies_async())
