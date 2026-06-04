import asyncio
import uuid
import sys
from sqlalchemy import text
from db.connection import AsyncSessionLocal
from schemas.job import JobData
from workers.crawlers import crawl_company_task

# Import adapters
from scrapers.amazon.adapter import scrape_amazon_jobs
from scrapers.google.adapter import scrape_google_careers
from scrapers.meta.adapter import scrape_meta_careers
from scrapers.microsoft.adapter import scrape_microsoft_careers
from scrapers.remoteok.adapter import scrape_remoteok
from scrapers.weworkremotely.adapter import scrape_weworkremotely

# Import seed lists
from discovery.seed_lists import ALL_SEED_LISTS

async def seed_all_companies():
    async with AsyncSessionLocal() as session:
        for seed_list in ALL_SEED_LISTS:
            for comp in seed_list:
                # We only fully support these for ATS
                if comp["ats_type"] not in ["greenhouse", "lever", "ashby", "workable"]:
                    continue

                res = await session.execute(text("SELECT id FROM companies WHERE ats_slug = :slug"), {"slug": comp["ats_slug"]})
                row = res.fetchone()
                if not row:
                    comp_id = str(uuid.uuid4())
                    await session.execute(text("""
                        INSERT INTO companies (id, name, domain, ats_type, ats_slug, size_tier, country, crawl_status)
                        VALUES (:id, :name, :domain, :ats_type, :ats_slug, 'startup', 'US', 'active')
                    """), {
                        "id": comp_id,
                        "name": comp["name"],
                        "domain": comp.get("domain", comp["name"].lower() + ".com"),
                        "ats_type": comp["ats_type"],
                        "ats_slug": comp["ats_slug"],
                    })
                    print(f"Inserted {comp['name']}")
                else:
                    comp_id = str(row.id)
                    print(f"Skipped {comp['name']} (already exists)")
                    
                print(f"Queueing scrape task for {comp['name']}...")
                crawl_company_task.delay(comp_id)
        await session.commit()

async def run_direct_scrapers():
    queries = ["Intern", "Internship", "Student"]
    all_jobs = []

    async def fetch_and_convert(scraper_func, query, location=""):
        try:
            print(f"Running {scraper_func.__name__} for '{query}'...")
            dict_jobs = await scraper_func(query, location)
            print(f"Got {len(dict_jobs)} jobs from {scraper_func.__name__}")
            for j in dict_jobs:
                # Force job_type to internship for these specific queries
                job_type = "internship"
                all_jobs.append(JobData(
                    external_id=str(j.get("external_job_id", uuid.uuid4())),
                    title=j.get("title", "Unknown"),
                    description=j.get("description", ""),
                    apply_url=j.get("apply_url", j.get("url", "")),
                    source=j.get("source", "unknown"),
                    job_type=job_type,
                    location=j.get("location", ""),
                    is_remote=j.get("is_remote", False),
                    company_slug=j.get("company", "").lower(),
                    company_name=j.get("company", ""),
                    raw_data=j
                ))
        except Exception as e:
            print(f"Error in {scraper_func.__name__} for '{query}': {e}")

    tasks = []
    for query in queries:
        tasks.append(fetch_and_convert(scrape_amazon_jobs, query))
        tasks.append(fetch_and_convert(scrape_microsoft_careers, query))
        tasks.append(fetch_and_convert(scrape_google_careers, query))
        tasks.append(fetch_and_convert(scrape_meta_careers, query))

    # Run in parallel chunks of 5 to avoid overwhelming APIs
    chunk_size = 5
    for i in range(0, len(tasks), chunk_size):
        await asyncio.gather(*tasks[i:i+chunk_size])
        await asyncio.sleep(2)

    if all_jobs:
        from db.database import async_save_jobs
        await async_save_jobs(all_jobs)
        print(f"Upserted {len(all_jobs)} jobs.")

async def main():
    print("Seeding and queuing all ATS companies...")
    await seed_all_companies()
    print("Running direct scrapers for Big Tech and Remote sites...")
    await run_direct_scrapers()
    print("Mega scrape completed!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
