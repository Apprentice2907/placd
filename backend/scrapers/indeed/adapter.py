import asyncio
import logging
import pandas as pd
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, is_valid_apply_url

log = logging.getLogger(__name__)

INDEED_SEARCHES = [
    {"keywords": "software engineer", "location": "India"},
    {"keywords": "data engineer", "location": "India"},
    {"keywords": "product manager", "location": "India"},
    {"keywords": "frontend engineer", "location": "India"},
    {"keywords": "backend engineer", "location": "India"},
    {"keywords": "software engineer", "location": "Remote"},
]

class IndeedAdapter(UnifiedAdapter):
    source = "indeed"
    rpm = 30
    api_domain = "indeed.com"

    async def fetch_jobs(self) -> list[dict]:
        jobs = []
        try:
            import jobspy
            log.info("Using JobSpy for Indeed scraping")
            
            for search in INDEED_SEARCHES:
                jobs_df = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: jobspy.scrape_jobs(
                        site_name=["indeed"],
                        search_term=search["keywords"],
                        location=search["location"],
                        results_wanted=200,
                        hours_old=48,
                        verbose=0,
                    )
                )
                
                if jobs_df is not None and not jobs_df.empty:
                    for _, row in jobs_df.iterrows():
                        apply_url = row.get("job_url", "")
                        if not is_valid_apply_url(apply_url):
                            continue
                            
                        jobs.append({
                            "title": row.get("title", ""),
                            "company": row.get("company", ""),
                            "location": row.get("location", ""),
                            "description": clean_description(row.get("description", "")),
                            "url": apply_url,
                            "apply_url": apply_url,
                            "source": self.source,
                            "posted_date": row.get("date_posted") if not pd.isna(row.get("date_posted")) else None,
                            "job_type": row.get("job_type", "full-time") if not pd.isna(row.get("job_type")) else "full-time",
                            "source_priority": 1
                        })
                await asyncio.sleep(2)
            log.info(f"[Indeed] Fetched {len(jobs)} jobs total")
            return jobs
        except Exception as e:
            log.error(f"[Indeed] Scrape failed: {e}")
            return []

if __name__ == "__main__":
    adapter = IndeedAdapter()
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
