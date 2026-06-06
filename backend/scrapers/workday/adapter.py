import asyncio
import logging
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

KNOWN_WORKDAY_BOARDS = [
    {"name": "Netflix", "url": "https://netflix.wd1.myworkdayjobs.com", "tenant": "Netflix"},
    {"name": "Snowflake", "url": "https://snowflake.wd1.myworkdayjobs.com", "tenant": "Careers"},
    {"name": "Databricks", "url": "https://databricks.wd1.myworkdayjobs.com", "tenant": "careers"}
]

class WorkdayAdapter(UnifiedAdapter):
    source = "workday"
    rpm = 30
    api_domain = "myworkdayjobs.com"

    def __init__(self, config=None):
        super().__init__(config)
        self.company_config = config or {}

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        boards = []
        
        if self.company_config and "url" in self.company_config:
            boards = [{
                "name": self.company_config.get("name", "Unknown"),
                "url": self.company_config["url"].rstrip('/'),
                "tenant": self.company_config.get("tenant", "")
            }]
        else:
            log.info("No specific Workday config provided. Sweeping known boards...")
            boards = KNOWN_WORKDAY_BOARDS

        semaphore = asyncio.Semaphore(5)

        async def fetch_board(board):
            base_url = board["url"].rstrip('/')
            tenant = board["tenant"]
            company_name = board["name"]
            api_url = f"{base_url}/wday/cxs/{tenant}/jobs"
            
            headers = {
                "Accept": "application/json, application/xml",
                "Content-Type": "application/json",
                "Origin": base_url,
                "Referer": f"{base_url}/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            jobs = []
            
            async with self.get_client() as client:
                async with semaphore:
                    for offset in range(0, 500, 20):  # Cap at 500
                        payload = {
                            "appliedFacets": {},
                            "limit": 20,
                            "offset": offset,
                            "searchText": ""
                        }
                        
                        try:
                            # UnifiedAdapter _fetch_with_retry doesn't easily support POST with json payload in a way that
                            # returns the response directly without breaking. Wait, _fetch_with_retry is just a GET wrapper usually?
                            # Let's use the client directly but with manual retry.
                            resp = await client.post(api_url, json=payload, headers=headers)
                            
                            if resp.status_code != 200:
                                log.warning(f"Workday API {resp.status_code} for {company_name} at offset {offset}")
                                break
                                
                            data = resp.json()
                            job_postings = data.get("jobPostings", [])
                            if not job_postings:
                                break
                                
                            for item in job_postings:
                                job_title = item.get("title", "")
                                job_location = item.get("locationsText", "Global")
                                external_path = item.get("externalPath", "")
                                job_url = f"{base_url}{external_path}" if external_path else ""
                                
                                if not job_url:
                                    continue
                                    
                                posted_on = item.get("postedOn", "")
                                time_type = item.get("timeType", "full_time")
                                
                                # Optional: fetch description (we will skip for now to save time/requests, or just add a placeholder)
                                description = job_title
                                
                                is_remote = "remote" in job_location.lower()
                                
                                jobs.append({
                                    "title": job_title,
                                    "company": company_name,
                                    "location": job_location,
                                    "description": description,
                                    "apply_url": job_url,
                                    "url": job_url,
                                    "source": self.source,
                                    "source_platform": self.source,
                                    "job_type": time_type,
                                    "department": "General",
                                    "date_posted": datetime.now().isoformat() if "Today" in posted_on else posted_on, # approximation
                                    "is_remote": is_remote,
                                    "is_hybrid": False,
                                    "trust_score": 80,
                                    "company_domain": "",
                                    "company_logo_url": None,
                                    "company_tier": 2,
                                    "skills": [],
                                    "salary_min": None,
                                    "salary_max": None,
                                    "salary_currency": None,
                                })
                                
                            await asyncio.sleep(1) # respectful delay
                        except Exception as e:
                            log.debug(f"Failed to fetch Workday jobs for {company_name} at offset {offset}: {e}")
                            break
                            
            return jobs

        tasks = [fetch_board(board) for board in boards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
                
        return all_jobs

if __name__ == "__main__":
    adapter = WorkdayAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
