import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class AppleAdapter(UnifiedAdapter):
    source = "apple"
    company = "Apple"
    rpm = 20
    api_domain = "apple.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch jobs from Apple Careers JSON API.
        Must use JSON API with appropriate payload.
        """
        url = "https://jobs.apple.com/api/v1/jobDetails/search"
        jobs = []
        
        # Apple's API expects CSRF headers which are typically retrieved by hitting the homepage first.
        # However, for this adapter, we'll try a direct fetch using GET or POST as per the instruction.
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://jobs.apple.com/",
            "Content-Type": "application/json",
            "Origin": "https://jobs.apple.com"
        }
        
        payload = {
            "query": "",
            "filters": {
                "range": {
                    "standard": 50
                }
            },
            "page": 1,
            "sort": "newest"
        }
        
        async with self.get_client() as client:
            try:
                # Some API paths use GET with parameters, some use POST with JSON.
                # The user instruction specifies GET with payload.
                # In httpx, you can pass `json=...` even in GET, or it could be a typo for POST.
                # We will use POST because 401 implies the endpoint exists for POST but requires auth/CSRF.
                
                # Try getting CSRF token from a session ping
                try:
                    await client.get("https://jobs.apple.com/en-us/search", headers=headers)
                    if "X-Apple-CSRF-Token" in client.cookies:
                        headers["X-Apple-CSRF-Token"] = client.cookies["X-Apple-CSRF-Token"]
                except Exception:
                    pass
                
                # Fetch up to 5 pages
                for page in range(1, 6):
                    payload["page"] = page
                    # Attempt POST
                    resp = await client.post("https://jobs.apple.com/api/role/search", json=payload, headers=headers)
                    
                    if resp.status_code != 200:
                        log.warning(f"Failed to fetch Apple jobs. Status: {resp.status_code}")
                        break
                        
                    data = resp.json()
                    search_results = data.get("searchResults", [])
                    
                    if not search_results:
                        break
                        
                    for item in search_results:
                        job_title = item.get("postingTitle", "")
                        job_id = item.get("positionId", "")
                        
                        location = item.get("locationName", "Remote")
                        is_remote = "remote" in location.lower()
                        
                        apply_url = f"https://jobs.apple.com/en-us/details/{job_id}"
                        
                        posted_date_str = item.get("postingDate", "")
                        
                        jobs.append({
                            "title": job_title,
                            "company": "Apple",
                            "location": location,
                            "description": job_title, # Apple doesn't return full desc in list
                            "apply_url": apply_url,
                            "url": apply_url,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": "full_time",
                            "department": item.get("teamName", "General"),
                            "date_posted": posted_date_str or datetime.now().isoformat(),
                            "is_remote": is_remote,
                            "is_hybrid": False,
                            "trust_score": 90,
                            "company_domain": "apple.com",
                            "company_logo_url": None,
                            "company_tier": 1,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None,
                        })
                    
                    await asyncio.sleep(2)
                    
            except Exception as e:
                log.warning(f"Failed to scrape Apple: {e}")
                
        return jobs

if __name__ == "__main__":
    adapter = AppleAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
