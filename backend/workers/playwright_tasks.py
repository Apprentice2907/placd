import asyncio
import structlog
from celery import shared_task

from scrapers.playwright.config import PLAYWRIGHT_ENABLED
from scrapers.playwright.pool import PlaywrightPool
from scrapers.playwright.linkedin import LinkedInScraper
from scrapers.playwright.wellfound import WellfoundScraper

from db.database import async_save_jobs
from db.connection import AsyncSessionLocal
from utils.async_utils import run_async

logger = structlog.get_logger(__name__)

# Singleton pool for the worker process
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = PlaywrightPool()
    return _pool

async def _scrape_linkedin(query: str, location: str):
    if not PLAYWRIGHT_ENABLED:
        logger.info("playwright_disabled", msg="Skipping linkedin scrape.")
        return
        
    logger.info("linkedin_task_started", query=query, location=location)
    pool = get_pool()
    
    try:
        async with pool.get_context() as context:
            scraper = LinkedInScraper(context)
            jobs = await scraper.search_jobs(query, location)
            
            if jobs:
                async with AsyncSessionLocal() as session:
                    inserted, updated = await async_save_jobs(jobs, db_session=session)
                    logger.info("linkedin_task_saved", inserted=inserted, updated=updated)
    except Exception as e:
        logger.error("linkedin_task_error", error=str(e))

@shared_task(name="scrape_linkedin_task", rate_limit='10/m')
def scrape_linkedin_task(query: str, location: str):
    """Scrape LinkedIn search via Playwright."""
    run_async(_scrape_linkedin(query, location))


async def _scrape_wellfound():
    if not PLAYWRIGHT_ENABLED:
        logger.info("playwright_disabled", msg="Skipping wellfound scrape.")
        return
        
    logger.info("wellfound_task_started")
    pool = get_pool()
    
    roles = ['software engineer', 'data scientist', 'ml engineer', 'product manager']
    all_jobs = []
    
    try:
        async with pool.get_context() as context:
            scraper = WellfoundScraper(context)
            for role in roles:
                jobs = await scraper.search_jobs(query=role, role_types=['Full time', 'Internship'])
                all_jobs.extend(jobs)
                # Polite delay between roles
                await asyncio.sleep(5)
                
            if all_jobs:
                async with AsyncSessionLocal() as session:
                    inserted, updated = await async_save_jobs(all_jobs, db_session=session)
                    logger.info("wellfound_task_saved", inserted=inserted, updated=updated)
    except Exception as e:
        logger.error("wellfound_task_error", error=str(e))

@shared_task(name="scrape_wellfound_task")
def scrape_wellfound_task():
    """Scrape specific roles on Wellfound via Playwright."""
    run_async(_scrape_wellfound())
