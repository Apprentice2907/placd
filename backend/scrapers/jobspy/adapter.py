import jobspy
import asyncio
from typing import List, Dict, Any
import pandas as pd
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, is_valid_apply_url

# Search matrix — run ALL combinations:
SEARCH_TERMS = [
    # Engineering
    "software engineer", "backend engineer", "frontend engineer",
    "full stack developer", "mobile developer", "android developer",
    "ios developer", "flutter developer", "react native developer",
    # Data
    "data engineer", "data scientist", "machine learning engineer",
    "mlops engineer", "analytics engineer", "business intelligence",
    # Infrastructure  
    "devops engineer", "site reliability engineer", "platform engineer",
    "cloud engineer", "security engineer", "network engineer",
    # Specialised
    "blockchain developer", "smart contract developer", "game developer",
    "embedded systems engineer", "firmware engineer", "robotics engineer",
    # Management
    "engineering manager", "tech lead", "product manager", "program manager",
    # Design
    "ui ux designer", "product designer", "graphic designer",
]

LOCATIONS = [
    # India cities
    "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai",
    "Kolkata", "Ahmedabad", "Noida", "Gurgaon",
    # Remote
    "Remote",
    # Global (for international jobs)
    "United States", "United Kingdom", "Germany", "Singapore", "Canada",
]

SITES = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]

class JobSpyAdapter(UnifiedAdapter):
    source = "jobspy"
    rpm = 10  # conservative, jobspy has its own internal limiting

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        all_jobs = []
        import logging
        logger = logging.getLogger(__name__)

        for term in SEARCH_TERMS:
            for location in LOCATIONS:
                try:
                    country_indeed = "India"
                    if location == "Remote":
                        country_indeed = "USA"
                    elif location in ["United States", "United Kingdom", "Germany", "Singapore", "Canada"]:
                        country_indeed = "USA" if location == "United States" else location

                    # Run in thread pool (jobspy is sync)
                    jobs_df = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: jobspy.scrape_jobs(
                            site_name=SITES,
                            search_term=term,
                            location=location,
                            results_wanted=100,
                            hours_old=48,  # only recent jobs
                            country_indeed=country_indeed,
                            linkedin_fetch_description=True,
                            verbose=0,
                        )
                    )
                    if jobs_df is not None and not jobs_df.empty:
                        normalized = self._normalize_jobspy(jobs_df, term, location)
                        all_jobs.extend(normalized)
                        logger.info(
                            "scrape_complete",
                            source="jobspy",
                            company="global",
                            jobs_found=len(normalized),
                            term=term,
                            location=location
                        )
                    await asyncio.sleep(2)  # polite delay between searches
                except Exception as e:
                    logger.error(
                        "scraper_failure",
                        source="jobspy",
                        company="global",
                        error=str(e),
                        term=term,
                        location=location
                    )
        return all_jobs

    def _normalize_jobspy(self, df, term, location) -> List[Dict[str, Any]]:
        jobs = []
        for _, row in df.iterrows():
            apply_url = row.get("job_url", "")
            if not is_valid_apply_url(apply_url):
                continue
                
            desc = clean_description(row.get("description", ""))
            if len(desc) < 50:
                continue

            jobs.append({
                "title": row.get("title", ""),
                "company": row.get("company", ""),
                "location": row.get("location", location),
                "description": desc,
                "salary_min": row.get("min_amount") if not pd.isna(row.get("min_amount")) else 0,
                "salary_max": row.get("max_amount") if not pd.isna(row.get("max_amount")) else 0,
                "salary_currency": row.get("currency", "INR") if not pd.isna(row.get("currency")) else "INR",
                "job_type": row.get("job_type", "") if not pd.isna(row.get("job_type")) else "",
                "is_remote": row.get("is_remote", False),
                "apply_url": apply_url,
                "date_posted": row.get("date_posted") if not pd.isna(row.get("date_posted")) else None,
                "source": row.get("site", "indeed"),
                "source_platform": "jobspy",
            })
        return jobs

if __name__ == "__main__":
    import pandas as pd
    adapter = JobSpyAdapter(company_config={"name": "global"})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"Total: {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
