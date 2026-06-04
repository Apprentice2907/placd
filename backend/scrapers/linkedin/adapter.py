import os
import asyncio
import logging
from bs4 import BeautifulSoup
import httpx
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, is_valid_apply_url

log = logging.getLogger(__name__)

LINKEDIN_SEARCHES = [
    {"keywords": "software engineer", "location": "India"},
    {"keywords": "data engineer", "location": "India"},
    {"keywords": "devops engineer", "location": "India"},
    {"keywords": "product manager", "location": "India"},
    {"keywords": "software engineer", "location": "Remote"},
    {"keywords": "machine learning engineer", "location": "India"},
    # Expanded based on user request...
    {"keywords": "frontend engineer", "location": "India"},
    {"keywords": "backend engineer", "location": "India"},
    {"keywords": "full stack developer", "location": "India"},
    {"keywords": "data scientist", "location": "India"},
    {"keywords": "ui ux designer", "location": "India"},
]

class LinkedinAdapter(UnifiedAdapter):
    source = "linkedin"
    rpm = 30
    api_domain = "linkedin.com"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        apify_token = os.environ.get("APIFY_TOKEN")
        
        if apify_token:
            log.info("Using Apify for LinkedIn scraping (Priority 1)")
            all_jobs = await self._scrape_with_apify(apify_token)
        else:
            try:
                import jobspy
                log.info("Using JobSpy for LinkedIn scraping (Priority 2)")
                all_jobs = await self._scrape_with_jobspy()
            except ImportError:
                log.warning("JobSpy not available. Falling back to unofficial API (Priority 3)")
                all_jobs = await self._scrape_with_unofficial_api()
                
        # Deduplication happens in base_adapter save_to_db, but we can do a quick unique check here
        unique_jobs = []
        seen = set()
        for job in all_jobs:
            if job["apply_url"] not in seen:
                seen.add(job["apply_url"])
                unique_jobs.append(job)
                
        return unique_jobs

    async def _scrape_with_apify(self, token: str) -> list[dict]:
        try:
            from apify_client import ApifyClientAsync
            client = ApifyClientAsync(token)
            jobs = []
            
            for search in LINKEDIN_SEARCHES:
                run_input = {
                    "queries": f"{search['keywords']} in {search['location']}",
                    "publishedAt": "past-24-hours",
                    "maxItems": 100
                }
                
                run = await client.actor("apify/linkedin-jobs-scraper").call(run_input=run_input)
                async for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    apply_url = item.get("jobUrl", "")
                    if not is_valid_apply_url(apply_url):
                        continue
                        
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("companyName", ""),
                        "location": item.get("location", ""),
                        "description": clean_description(item.get("description", "")),
                        "url": apply_url,
                        "apply_url": apply_url,
                        "source": self.source,
                        "posted_date": item.get("publishedAt", ""),
                        "job_type": item.get("employmentType", "full-time"),
                        "source_priority": 1
                    })
            return jobs
        except Exception as e:
            log.error(f"Apify LinkedIn scrape failed: {e}")
            return []

    async def _scrape_with_jobspy(self) -> list[dict]:
        jobs = []
        try:
            import jobspy
            import pandas as pd
            for search in LINKEDIN_SEARCHES:
                jobs_df = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: jobspy.scrape_jobs(
                        site_name=["linkedin"],
                        search_term=search["keywords"],
                        location=search["location"],
                        results_wanted=100,
                        hours_old=48,
                        linkedin_fetch_description=True,
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
                            "source_priority": 2
                        })
                await asyncio.sleep(2)
            return jobs
        except Exception as e:
            log.error(f"JobSpy LinkedIn scrape failed: {e}")
            return []

    async def _scrape_with_unofficial_api(self) -> list[dict]:
        jobs = []
        async with self.get_client() as client:
            for search in LINKEDIN_SEARCHES:
                keywords = search["keywords"]
                location = search["location"]
                
                for offset in range(0, 100, 25): # Paginate 0, 25, 50, 75
                    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&start={offset}"
                    try:
                        resp = await self._fetch_with_retry(client, url)
                        if not resp.text.strip():
                            break # No more jobs
                            
                        soup = BeautifulSoup(resp.text, "html.parser")
                        cards = soup.find_all("li")
                        
                        if not cards:
                            break
                            
                        for card in cards:
                            title_elem = card.find("h3", class_="base-search-card__title")
                            company_elem = card.find("h4", class_="base-search-card__subtitle")
                            location_elem = card.find("span", class_="job-search-card__location")
                            url_elem = card.find("a", class_="base-card__full-link")
                            date_elem = card.find("time", class_="job-search-card__listdate")
                            
                            if not title_elem or not url_elem:
                                continue
                                
                            job_url = url_elem.get("href", "").split("?")[0]
                            if not is_valid_apply_url(job_url):
                                continue
                                
                            jobs.append({
                                "title": title_elem.get_text(strip=True),
                                "company": company_elem.get_text(strip=True) if company_elem else "",
                                "location": location_elem.get_text(strip=True) if location_elem else "",
                                "description": "", # Unofficial API doesn't give description easily here
                                "url": job_url,
                                "apply_url": job_url,
                                "source": self.source,
                                "posted_date": date_elem.get("datetime", "") if date_elem else None,
                                "job_type": "full-time",
                                "source_priority": 3
                            })
                            
                        await asyncio.sleep(1)
                    except Exception as e:
                        log.error(f"Unofficial LinkedIn API fetch failed for offset {offset}: {e}")
                        break # Stop pagination on error
                        
        return jobs

if __name__ == "__main__":
    adapter = LinkedinAdapter()
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
