import structlog
from celery import shared_task
from sqlalchemy import text
from db.connection import AsyncSessionLocal

from workers.celery_config import app as celery, default_retry_countdown
from utils.async_utils import run_async

# ── ATS Crawlers (existing) ──────────────────────────────────────────────────
from scrapers.ats.greenhouse import GreenhouseCrawler
from scrapers.ats.lever import LeverCrawler
from scrapers.ats.ashby import AshbyCrawler
from scrapers.ats.workable import WorkableCrawler

# ── New Adapters (Task 4) ────────────────────────────────────────────────────
from scrapers.bamboohr.adapter import BambooHRAdapter
from scrapers.recruitee.adapter import RecruiteeAdapter
from scrapers.himalayas.adapter import HimalayasAdapter
from scrapers.cutshort.adapter import CutshortAdapter
from scrapers.instahyre.adapter import scrape_instahyre

logger = structlog.get_logger(__name__)


def get_crawler(ats_type: str, slug: str = None):
    """Factory to return the appropriate crawler instance."""
    if ats_type == "greenhouse":
        from scrapers.greenhouse.adapter import GreenhouseAdapter
        return GreenhouseAdapter({"name": slug or ats_type, "board_token": slug})
    elif ats_type == "lever":
        from scrapers.lever.adapter import LeverAdapter
        return LeverAdapter({"name": slug or ats_type, "board_token": slug})
    elif ats_type == "ashby":
        from scrapers.ashby.adapter import AshbyAdapter
        return AshbyAdapter({"name": slug or ats_type, "board_token": slug})
    elif ats_type == "workday":
        from scrapers.workday.adapter import WorkdayAdapter
        return WorkdayAdapter({"name": slug or ats_type, "board_token": slug})
    elif ats_type == "bamboohr":
        from scrapers.bamboohr.adapter import BambooHRAdapter
        return BambooHRAdapter({"name": slug or ats_type, "board_token": slug})
    elif ats_type == "recruitee":
        from scrapers.recruitee.adapter import RecruiteeAdapter
        return RecruiteeAdapter({"name": slug or ats_type, "board_token": slug})
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Generic company crawl (greenhouse / lever / ashby / workable via DB lookup)
# ─────────────────────────────────────────────────────────────────────────────

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

        crawler = get_crawler(ats_type, ats_slug)
        if not crawler:
            logger.warning("unsupported_ats_type", ats_type=ats_type, company_id=company_id)
            return

        try:
            # Crawl
            jobs = await crawler.fetch_jobs()

            # Save
            from db.database import async_save_jobs
            inserted, updated = await async_save_jobs(jobs, company_id=company_id, db_session=session)

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


@celery.task(bind=True, name="crawl_company_task", rate_limit='100/m', max_retries=3)
def crawl_company_task(self, company_id: str):
    """Celery task to crawl a single company."""
    try:
        run_async(_crawl_company_async(company_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch all companies
# ─────────────────────────────────────────────────────────────────────────────

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


@celery.task(bind=True, name="crawl_all_companies_task", max_retries=3)
def crawl_all_companies_task(self):
    """Celery task to find companies due for crawling and dispatch them."""
    try:
        run_async(_crawl_all_companies_async())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ─────────────────────────────────────────────────────────────────────────────
# Discovered Companies Crawl
# ─────────────────────────────────────────────────────────────────────────────

async def _crawl_discovered_company_async(slug: str, platform: str):
    logger.info("starting_discovered_company_crawl", slug=slug, platform=platform)
    
    crawler = get_crawler(platform, slug)
    if not crawler:
        logger.warning("unsupported_platform", platform=platform, slug=slug)
        return
        
    async with AsyncSessionLocal() as session:
        try:
            jobs = await crawler.fetch_jobs()
            
            # Save jobs (company_id is None since it's just discovered)
            from db.database import async_save_jobs
            inserted, updated = await async_save_jobs(jobs, db_session=session)
            
            # Update discovered_companies to active
            await session.execute(
                text("""
                    UPDATE discovered_companies 
                    SET scrape_status = 'active', last_scraped_at = NOW(), job_count_last = :job_count
                    WHERE slug = :slug AND platform = :platform
                """),
                {"slug": slug, "platform": platform, "job_count": len(jobs)}
            )
            
            # Upsert into main companies table
            await session.execute(
                text("""
                    INSERT INTO companies (name, domain, ats_type, ats_slug, crawl_status, last_crawled_at)
                    VALUES (:name, :domain, :platform, :slug, 'active', NOW())
                    ON CONFLICT (domain) DO UPDATE SET
                        last_crawled_at = NOW(),
                        crawl_status = 'active'
                """),
                {
                    "name": slug.replace("-", " ").title(),
                    "domain": f"{slug}.com",
                    "platform": platform,
                    "slug": slug
                }
            )
            
            await session.commit()
            logger.info("discovered_company_crawl_success", slug=slug, inserted=inserted)
            
        except Exception as e:
            logger.error("discovered_company_crawl_failed", slug=slug, error=str(e))
            await session.rollback()
            await session.execute(
                text("""
                    UPDATE discovered_companies 
                    SET scrape_status = 'dead', last_scraped_at = NOW()
                    WHERE slug = :slug AND platform = :platform
                """),
                {"slug": slug, "platform": platform}
            )
            await session.commit()

@celery.task(bind=True, name="crawl_discovered_company_task", max_retries=3)
def crawl_discovered_company_task(self, slug: str, platform: str):
    try:
        run_async(_crawl_discovered_company_async(slug, platform))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))

async def _scrape_all_discovered_companies_async():
    logger.info("starting_scrape_all_discovered")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT slug, platform 
                FROM discovered_companies 
                WHERE scrape_status = 'pending' 
                   OR (scrape_status = 'active' AND last_scraped_at < NOW() - INTERVAL '6 hours')
                LIMIT 500
            """)
        )
        companies = result.fetchall()
        
    for index, row in enumerate(companies):
        delay = index * 2
        crawl_discovered_company_task.apply_async(args=[row.slug, row.platform], countdown=delay)

@celery.task(bind=True, name="scrape_all_discovered_companies")
def scrape_all_discovered_companies(self):
    run_async(_scrape_all_discovered_companies_async())


# ═════════════════════════════════════════════════════════════════════════════
# NEW SCRAPERS — Task 4 adapters registered as Celery tasks
# ═════════════════════════════════════════════════════════════════════════════

# ── BambooHR (crawl_tier_a) ──────────────────────────────────────────────────

async def _crawl_bamboohr_async(company_slug: str):
    logger.info("bamboohr_crawl_started", company=company_slug)
    adapter = BambooHRAdapter({"name": company_slug})
    jobs = await adapter.fetch_jobs()
    logger.info("bamboohr_crawl_done", company=company_slug, jobs_found=len(jobs))
    return jobs


@celery.task(bind=True, name="crawl_bamboohr_task", max_retries=3)
def crawl_bamboohr_task(self, company_slug: str):
    """Crawl a BambooHR company careers page."""
    try:
        run_async(_crawl_bamboohr_async(company_slug))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ── Recruitee (crawl_tier_a) ─────────────────────────────────────────────────

async def _crawl_recruitee_async(company_slug: str):
    logger.info("recruitee_crawl_started", company=company_slug)
    adapter = RecruiteeAdapter({"name": company_slug})
    jobs = await adapter.fetch_jobs()
    logger.info("recruitee_crawl_done", company=company_slug, jobs_found=len(jobs))
    return jobs


@celery.task(bind=True, name="crawl_recruitee_task", max_retries=3)
def crawl_recruitee_task(self, company_slug: str):
    """Crawl a Recruitee company offers page."""
    try:
        run_async(_crawl_recruitee_async(company_slug))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ── Himalayas (crawl_tier_a) ─────────────────────────────────────────────────

async def _crawl_himalayas_async(max_jobs: int = 500):
    logger.info("himalayas_crawl_started")
    adapter = HimalayasAdapter({"name": "himalayas", "max_jobs": max_jobs})
    jobs = await adapter.fetch_jobs()
    logger.info("himalayas_crawl_done", jobs_found=len(jobs))
    return jobs


@celery.task(bind=True, name="crawl_himalayas_task", max_retries=3)
def crawl_himalayas_task(self, max_jobs: int = 500):
    """Crawl the Himalayas remote job board."""
    try:
        run_async(_crawl_himalayas_async(max_jobs))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ── Cutshort (crawl_tier_b) ──────────────────────────────────────────────────

async def _crawl_cutshort_async(max_pages: int = 5):
    logger.info("cutshort_crawl_started")
    adapter = CutshortAdapter({"name": "cutshort", "max_pages": max_pages})
    jobs = await adapter.fetch_jobs()
    logger.info("cutshort_crawl_done", jobs_found=len(jobs))
    return jobs


@celery.task(bind=True, name="crawl_cutshort_task", max_retries=3)
def crawl_cutshort_task(self, max_pages: int = 5):
    """Crawl Cutshort job listings."""
    try:
        run_async(_crawl_cutshort_async(max_pages))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ── Instahyre (crawl_tier_b) ─────────────────────────────────────────────────

@celery.task(bind=True, name="crawl_instahyre_task", max_retries=3)
def crawl_instahyre_task(self, max_pages: int = 5):
    """Crawl Instahyre using curl_cffi impersonation."""
    try:
        run_async(scrape_instahyre(max_pages=max_pages))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))


# ── Naukri Global (crawl_tier_b) ───────────────────────────────────────────────

@celery.task(bind=True, name="crawl_naukri_task", max_retries=3)
def crawl_naukri_task(self):
    """Crawl Naukri global search."""
    async def _crawl_naukri_async():
        logger.info("naukri_crawl_started")
        try:
            from scrapers.naukri.adapter import NaukriAdapter
            adapter = NaukriAdapter({"name": "naukri global", "max_pages": 50})
            jobs = await adapter.fetch_jobs()
            logger.info("naukri_crawl_done", jobs_found=len(jobs))
        except ImportError:
            logger.error("NaukriAdapter not found")
    try:
        run_async(_crawl_naukri_async())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))

# ── Internshala Global (crawl_tier_b) ──────────────────────────────────────────

@celery.task(bind=True, name="crawl_internshala_task", max_retries=3)
def crawl_internshala_task(self):
    """Crawl Internshala global search."""
    async def _crawl_internshala_async():
        logger.info("internshala_crawl_started")
        try:
            from scrapers.playwright.internshala import InternshalaScraper
            adapter = InternshalaScraper({"name": "internshala global", "max_pages": 20})
            jobs = await adapter.fetch_jobs()
            logger.info("internshala_crawl_done", jobs_found=len(jobs))
        except ImportError:
            logger.error("InternshalaScraper not found")
    try:
        run_async(_crawl_internshala_async())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))

# ── LinkedIn Global (crawl_tier_c) ─────────────────────────────────────────────

@celery.task(bind=True, name="scrape_linkedin_task", max_retries=3)
def scrape_linkedin_task(self):
    """Crawl LinkedIn global search."""
    async def _crawl_linkedin_async():
        logger.info("linkedin_crawl_started")
        try:
            from scrapers.playwright.linkedin import LinkedInScraper
            adapter = LinkedInScraper({"name": "linkedin global", "keywords": [
                "software engineer India", "backend engineer", "frontend engineer",
                "data engineer", "devops engineer", "machine learning engineer"
            ]})
            jobs = await adapter.fetch_jobs()
            logger.info("linkedin_crawl_done", jobs_found=len(jobs))
        except ImportError:
            logger.error("LinkedInScraper not found")
    try:
        run_async(_crawl_linkedin_async())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=default_retry_countdown(self.request.retries))

# ═════════════════════════════════════════════════════════════════════════════
# Batch dispatch for seed-list adapters (BambooHR, Recruitee, board scrapers)
# ═════════════════════════════════════════════════════════════════════════════

from discovery import enumerator

@celery.task(bind=True, name="run_full_discovery", queue="crawl_tier_a")
def run_full_discovery(self):
    """Run CommonCrawl CDX discovery for all ATS platforms.
    Discovers company slugs and saves to discovered_companies table.
    Expected to find: 8000+ Greenhouse, 3000+ Lever, 1500+ Ashby, 2000+ Workday slugs.
    Runtime: 30-60 minutes. Run weekly."""
    platforms = ["greenhouse", "lever", "ashby", "workday", "bamboohr", "recruitee"]
    for platform in platforms:
        run_async(enumerator.discover_platform(platform))

@celery.task(bind=True, name="crawl_all_new_adapters_task", max_retries=3)
def crawl_all_new_adapters_task(self):
    """
    Dispatch crawl tasks for every company in the BambooHR and Recruitee
    seed lists, plus one-off board-level scrapers (Himalayas, Cutshort,
    Instahyre).  Called by celery-beat or triggered manually.
    """
    from discovery.seed_lists import BAMBOOHR_COMPANIES, RECRUITEE_COMPANIES

    delay = 0

    # BambooHR companies
    for slug in BAMBOOHR_COMPANIES:
        crawl_bamboohr_task.apply_async(args=[slug], countdown=delay)
        delay += 3  # 3-second stagger

    # Recruitee companies
    for slug in RECRUITEE_COMPANIES:
        crawl_recruitee_task.apply_async(args=[slug], countdown=delay)
        delay += 3

    # Board-level scrapers (no per-company slug needed)
    crawl_himalayas_task.apply_async(countdown=delay)
    crawl_cutshort_task.apply_async(countdown=delay + 10)
    crawl_instahyre_task.apply_async(countdown=delay + 20)

    total = len(BAMBOOHR_COMPANIES) + len(RECRUITEE_COMPANIES) + 3
    logger.info("dispatched_new_adapter_tasks", total=total)

