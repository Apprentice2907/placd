import httpx
import logging
from datetime import datetime

from utils.config import REQUEST_TIMEOUT
from scrapers.shared.base_adapter import ATSAdapterBase

log = logging.getLogger(__name__)

class WorkdayAdapter(ATSAdapterBase):
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Fetch jobs from Workday's internal JSON API.
        """
        url = self.company_config.get("url", "")
        tenant = self.company_config.get("tenant", "")
        
        # Clean URL to avoid double slashes
        base_url = url.rstrip('/')
        api_url = f"{base_url}/wday/cxs/{tenant}/jobs"
        
        jobs = []
        try:
            # Most workday instances require specific headers
            headers = {
                "Accept": "application/json, application/xml",
                "Content-Type": "application/json",
                "Origin": base_url,
                "Referer": f"{base_url}/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            payload = {
                "appliedFacets": {},
                "limit": 50,
                "offset": 0,
                "searchText": query
            }
            
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                job_postings = data.get("jobPostings", [])
                for item in job_postings:
                    job_title = item.get("title", "")
                    
                    job_location = item.get("locationsText", "")
                    if location and location.lower() not in job_location.lower():
                        if location.lower() != "remote" or "remote" not in job_location.lower():
                            continue
                            
                    external_path = item.get("externalPath", "")
                    job_url = f"{base_url}{external_path}"
                    
                    description = ""
                    if external_path:
                        try:
                            desc_resp = await client.get(f"{base_url}/wday/cxs/{tenant}/job/{external_path}", headers=headers)
                            if desc_resp.status_code == 200:
                                desc_data = desc_resp.json()
                                description = desc_data.get("jobPostingInfo", {}).get("jobDescription", "")
                        except Exception as e:
                            log.debug(f"Failed to fetch workday desc for {job_url}: {e}")
                    
                    posted_on = item.get("postedOn", "")
                    time_type = item.get("timeType", "full-time")
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company_name,
                        "location": job_location,
                        "description": description,
                        "url": job_url,
                        "apply_url": job_url,
                        "source": "workday",
                        "posted_date": posted_on,
                        "job_type": time_type,
                        "salary": "",
                        "source_priority": self.priority,
                        "company_tags": self._format_tags(),
                        "company_type": self.company_type
                    })
                    
        except Exception as e:
            log.warning(f"Failed to scrape Workday for {self.company_name}: {e}")
            
        return jobs
