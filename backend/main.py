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
    success = False
    try:
        if inspect.isclass(func):
            # Instantiate adapter without specific company so it uses seed lists
            adapter = func()
            jobs = await adapter.fetch_jobs()
        else:
            jobs = await func(*args, **kwargs)
            
        inserted = await save_jobs(jobs, name.lower())
        skipped = len(jobs) - inserted
        log.info(f"[{name}] Fetched: {len(jobs)} jobs")
        log.info(f"[{name}] Inserted: {inserted} | Skipped: {skipped} | Failed: 0")
        success = len(jobs) > 0
    except Exception as e:
        log.error(f"[{name}] FAILED: {e}")
        log.info(f"[{name}] Inserted: 0 | Skipped: 0 | Failed: {len(jobs) if 'jobs' in locals() else 'unknown'}")

    try:
        from db.retention import record_scrape_result
        await record_scrape_result(name.lower(), success)
    except Exception as e:
        log.error(f"[{name}] Could not record scrape result: {e}")

async def run_scrape(target_source: str = None):
    from db.connection import engine
    from db.retention import STORAGE_STOP_SCRAPE_MB, database_size_mb, ensure_retention_schema
    async with engine.begin() as conn:
        await ensure_retention_schema(conn)
        size = await database_size_mb(conn)
    if size >= STORAGE_STOP_SCRAPE_MB:
        # The cleanup step that follows frees space, so this must not fail the run yet
        log.error(f"Skipping scrape: database is {size:.0f} MB, too close to Neon's limit")
        return

    scrapers = {}
    
    def safe_add(name, mod_path, obj_name, args, kwargs):
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            func = getattr(mod, obj_name)
            scrapers[name] = (func, args, kwargs)
        except Exception as e:
            log.error(f"[{name}] FAILED to import: {e}")

    safe_add("internshala", "scrapers.internshala.adapter", "InternshalaAdapter", [], {})
    safe_add("linkedin", "scrapers.linkedin.adapter", "LinkedinAdapter", [], {})
    safe_add("naukri", "scrapers.naukri.adapter", "NaukriAdapter", [], {})
    safe_add("wellfound", "scrapers.wellfound.adapter", "WellfoundAdapter", [], {})
    safe_add("himalayas", "scrapers.himalayas.adapter", "HimalayasAdapter", [], {})
    
    safe_add("amazon", "scrapers.amazon.adapter", "AmazonAdapter", [], {})
    safe_add("google", "scrapers.google.adapter", "GoogleAdapter", [], {})
    safe_add("meta", "scrapers.meta.adapter", "MetaAdapter", [], {})
    safe_add("microsoft", "scrapers.microsoft.adapter", "MicrosoftAdapter", [], {})
    safe_add("apple", "scrapers.apple.adapter", "AppleAdapter", [], {})
    
    safe_add("ashby", "scrapers.ashby.adapter", "AshbyAdapter", [], {})
    safe_add("greenhouse", "scrapers.greenhouse.adapter", "GreenhouseAdapter", [], {})
    safe_add("lever", "scrapers.lever.adapter", "LeverAdapter", [], {})
    safe_add("smartrecruiters", "scrapers.smartrecruiters.adapter", "SmartRecruitersAdapter", [], {})
    safe_add("workday", "scrapers.workday.adapter", "WorkdayAdapter", [], {})
    safe_add("bamboohr", "scrapers.bamboohr.adapter", "BambooHRAdapter", [], {})
    safe_add("recruitee", "scrapers.recruitee.adapter", "RecruiteeAdapter", [], {})
    
    safe_add("remoteok", "scrapers.remoteok.adapter", "RemoteOkAdapter", [], {})
    safe_add("weworkremotely", "scrapers.weworkremotely.adapter", "WeWorkRemotelyAdapter", [], {})
    safe_add("indeed", "scrapers.indeed.adapter", "IndeedAdapter", [], {})
    safe_add("ycombinator", "scrapers.ycombinator.adapter", "YCombinatorAdapter", [], {})
    safe_add("cutshort", "scrapers.cutshort.adapter", "CutshortAdapter", [], {})
    
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

async def review_reports(restore_id: str = None, reject_id: str = None):
    """Lists jobs hidden by user reports, or settles one of them."""
    from db.connection import engine
    from db.retention import ensure_retention_schema
    async with engine.begin() as conn:
        await ensure_retention_schema(conn)
        if restore_id:
            await conn.execute(text("UPDATE jobs SET status = 'active' WHERE id = :id AND status = 'under_review'"), {"id": restore_id})
            await conn.execute(text("DELETE FROM job_reports WHERE job_id = :id"), {"id": restore_id})
            print(f"Restored {restore_id}")
            return
        if reject_id:
            await conn.execute(text("UPDATE jobs SET is_spam = TRUE, spam_reason = 'confirmed_by_review', status = 'expired' WHERE id = :id"), {"id": reject_id})
            print(f"Removed {reject_id}")
            return
        rows = (await conn.execute(text("""
            SELECT j.id, j.title, j.company_name, j.apply_url, COUNT(r.job_id) AS reports
            FROM jobs j LEFT JOIN job_reports r ON r.job_id = j.id AND r.reason = 'scam'
            WHERE j.status = 'under_review'
            GROUP BY j.id, j.title, j.company_name, j.apply_url
            ORDER BY reports DESC
        """))).fetchall()
    print(f"{len(rows)} jobs waiting for review")
    for row in rows:
        print(f"{row.id} | {row.reports} reports | {row.title} | {row.company_name} | {row.apply_url}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action to run (e.g. scrape)")
    parser.add_argument("--source", help="Run specific scraper")
    parser.add_argument("--dry-run", action="store_true", help="cleanup: report only, change nothing")
    parser.add_argument("--trim-only", action="store_true", help="cleanup: shrink details, delete nothing")
    parser.add_argument("--compact", action="store_true", help="cleanup: return freed space to Neon")
    parser.add_argument("--restore", help="review-reports: put a reported job back on the site")
    parser.add_argument("--reject", help="review-reports: remove a reported job for good")
    args = parser.parse_args()
    
    if args.action == "scrape":
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_scrape(args.source))
    elif args.action == "cleanup":
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        from db.retention import run_cleanup
        asyncio.run(run_cleanup(args.dry_run, args.trim_only, args.compact))
    elif args.action == "review-reports":
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(review_reports(args.restore, args.reject))

if __name__ == "__main__":
    main()
