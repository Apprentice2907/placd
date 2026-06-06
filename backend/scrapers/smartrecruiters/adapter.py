import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class SmartRecruitersAdapter(UnifiedAdapter):
    source = "smartrecruiters"
    rpm = 30
    api_domain = "smartrecruiters.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch jobs directly from SmartRecruiters API.
        GET https://api.smartrecruiters.com/v1/companies/{board_token}/postings
        """
        board_token = getattr(self, "board_token", None)
        if not board_token and self.company_config:
            board_token = self.company_config.get("board_token", "")
            
        if not board_token:
            log.warning("No board_token provided for SmartRecruitersAdapter.")
            return []
            
        url = f"https://api.smartrecruiters.com/v1/companies/{board_token}/postings"
        jobs = []
        
        async with self.get_client() as client:
            try:
                resp = await self._fetch_with_retry(client, url)
                if resp.status_code != 200:
                    return []
                    
                data = resp.json()
                
                for item in data.get("content", []):
                    job_title = item.get("name", "")
                    
                    loc_obj = item.get("location", {})
                    city = loc_obj.get('city', '')
                    region = loc_obj.get('region', '')
                    country = loc_obj.get('country', '')
                    job_location = f"{city}, {region}, {country}".strip(", ")
                    
                    is_remote = False
                    if "remote" in str(loc_obj.get('remote', '')).lower() or "remote" in job_location.lower():
                        is_remote = True
                        
                    if not job_location and is_remote:
                        job_location = "Remote"
                            
                    job_url = f"https://careers.smartrecruiters.com/{board_token}/{item.get('id')}"
                    posted_date = item.get("releasedDate", datetime.now().isoformat())
                    
                    job_type_raw = item.get("typeOfEmployment", {}).get("label", "full_time")
                    job_type = self._normalize_job_type(job_type_raw, job_title)
                    
                    department = item.get("department", {}).get("label", "General")
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company or board_token,
                        "location": job_location,
                        "description": job_title, # Description requires a separate API call in SR
                        "apply_url": job_url,
                        "url": job_url,
                        "source": self.source,
                        "source_platform": self.source,
                        "job_type": job_type,
                        "department": department,
                        "date_posted": posted_date,
                        "is_remote": is_remote,
                        "is_hybrid": False,
                        "trust_score": 70,
                        "company_domain": "",
                        "company_logo_url": None,
                        "company_tier": 3,
                        "skills": [],
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": None,
                    })
                    
            except Exception as e:
                log.warning(f"Failed to scrape SmartRecruiters for {board_token}: {e}")
                
        return jobs

    def _normalize_job_type(self, raw: str, title: str = "") -> str:
        raw_lower = (raw or "").lower()
        title_lower = (title or "").lower()
        if "intern" in raw_lower or "intern" in title_lower:
            return "internship"
        if "part" in raw_lower:
            return "part_time"
        if "contract" in raw_lower:
            return "contract"
        return "full_time"

if __name__ == "__main__":
    adapter = SmartRecruitersAdapter({"name": "Atlassian", "board_token": "Atlassian"})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
