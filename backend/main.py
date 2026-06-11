import sys
import asyncio
import uuid
import re
import traceback
import argparse
import json
import logging
import inspect

from sqlalchemy import text
from db.connection import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("main")

async def print_quality_report():
    print("\n" + "="*60)
    print(" SCRAPE QUALITY REPORT ")
    print("="*60)
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("""
            SELECT 
              source,
              COUNT(*) as count_per_source
            FROM jobs
            WHERE status = 'active'
            GROUP BY source
        """))
        rows = res.fetchall()

    if not rows:
        print("No jobs found in database.")
    
    for row in rows:
        row_dict = dict(row._mapping)
        print(f"Source: {row_dict['source']}")
        print(f"  Total Jobs: {row_dict['count_per_source']}")
        print("-" * 60)
    print("\n")

def apply_data_quality_fallbacks(job: dict) -> dict:
    # 1. stipend_display
    if not job.get("stipend_display"):
        if job.get("is_internship") or job.get("job_type", "").lower() == "internship":
            job["stipend_display"] = "Unpaid"
        else:
            job["stipend_display"] = "Not mentioned"
            
    # 2. who_can_apply
    if not job.get("who_can_apply"):
        desc = job.get("description", "").lower()
        if "3rd year" in desc or "pre-final" in desc:
            job["who_can_apply"] = "3rd year or pre-final"
        elif "final year" in desc or "4th year" in desc:
            job["who_can_apply"] = "Final year students"
        elif "fresher" in desc or "0 experience" in desc:
            job["who_can_apply"] = "Freshers"
        else:
            job["who_can_apply"] = "Open to all"
            
    # 3. company_logo_url
    if not job.get("company_logo_url"):
        job["company_logo_url"] = ""
        
    # 4. skills
    if not job.get("skills"):
        common_tech = ["python", "react", "sql", "java", "javascript", "c++", "node", "aws", "docker", "kubernetes", "go", "ruby"]
        desc = job.get("description", "").lower()
        extracted = []
        for tech in common_tech:
            if re.search(rf"\b{tech}\b", desc):
                extracted.append(tech.title())
        job["skills"] = json.dumps(extracted) if extracted else json.dumps([])
    elif isinstance(job["skills"], list):
        job["skills"] = json.dumps(job["skills"])
        
    # 5. match_score (compute approximation or fallback)
    if job.get("match_score") is None:
        try:
            job["match_score"] = 0.65
        except:
            job["match_score"] = 0.65
            
    return job

async def save_jobs(jobs: list, source: str):
    """Save scraped jobs to PostgreSQL."""
    if not jobs:
        return 0
        
    for j in jobs:
        if isinstance(j, dict):
            apply_data_quality_fallbacks(j)
            
    from db.database import async_save_jobs
    inserted, updated = await async_save_jobs(jobs=jobs, source=source)
    return inserted

async def run_scraper_safe(name, func, *args, **kwargs):
    log.info(f"[{name}] Starting...")
    try:
        if inspect.isclass(func):
            # Instantiate adapter
            adapter = func({"name": "TestCompany", "board_token": "test"})
            jobs = await adapter.fetch_jobs()
        else:
            jobs = await func(*args, **kwargs)
            
        inserted = await save_jobs(jobs, name.lower())
        log.info(f"[{name}] Fetched {len(jobs)} jobs (Inserted {inserted})")
    except Exception as e:
        log.info(f"[{name}] FAILED: {e}")

async def run_scrape(target_source: str = None):
    scrapers = {}
    
    def safe_add(name, mod_path, obj_name, args, kwargs):
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            func = getattr(mod, obj_name)
            scrapers[name] = (func, args, kwargs)
        except Exception as e:
            log.error(f"[{name}] FAILED to import: {e}")

    safe_add("internshala", "scrapers.internshala.detailed", "scrape_internshala_detailed", ["software"], {"max_pages": 1})
    safe_add("linkedin", "scrapers.linkedin.apify_adapter", "scrape_linkedin_apify", ["software", "remote"], {})
    safe_add("naukri", "scrapers.naukri.adapter", "scrape_naukri", ["software", "remote"], {})
    safe_add("wellfound", "scrapers.wellfound.adapter", "scrape_wellfound", ["software", "remote"], {})
    
    safe_add("amazon", "scrapers.amazon.adapter", "scrape_amazon_jobs", ["software"], {})
    safe_add("google", "scrapers.google.adapter", "scrape_google_careers", ["software"], {})
    safe_add("meta", "scrapers.meta.adapter", "scrape_meta_careers", ["software"], {})
    safe_add("microsoft", "scrapers.microsoft.adapter", "scrape_microsoft_careers", ["software"], {})
    
    safe_add("ashby", "scrapers.ashby.adapter", "AshbyAdapter", [], {})
    safe_add("greenhouse", "scrapers.greenhouse.adapter", "GreenhouseAdapter", [], {})
    safe_add("lever", "scrapers.lever.adapter", "LeverAdapter", [], {})
    safe_add("smartrecruiters", "scrapers.smartrecruiters.adapter", "SmartRecruitersAdapter", [], {})
    safe_add("workday", "scrapers.workday.adapter", "WorkdayAdapter", [], {})
    
    safe_add("remoteok", "scrapers.remoteok.adapter", "scrape_remoteok", ["software"], {})
    safe_add("weworkremotely", "scrapers.weworkremotely.adapter", "scrape_weworkremotely", ["software"], {})
    
    # Opportunities needs a wrapper
    try:
        from scrapers.opportunities.opportunities_circle import OpportunitiesCircleScraper
        async def opps_wrapper():
            scraper = OpportunitiesCircleScraper()
            return await scraper.crawl_category("internships", limit=5)
        scrapers["opportunities"] = (opps_wrapper, [], {})
    except Exception as e:
        log.error(f"[opportunities] FAILED to import: {e}")

    
    tasks = []
    for name, (func, args, kwargs) in scrapers.items():
        if target_source and target_source.lower() != name.lower():
            continue
        tasks.append(run_scraper_safe(name, func, *args, **kwargs))
        
    await asyncio.gather(*tasks)
    
    await print_quality_report()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action to run (e.g. scrape)")
    parser.add_argument("--source", help="Run specific scraper")
    args = parser.parse_args()
    
    if args.action == "scrape":
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_scrape(args.source))

if __name__ == "__main__":
    main()
