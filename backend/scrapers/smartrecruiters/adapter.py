import httpx
import logging

from utils.config import REQUEST_TIMEOUT
from scrapers.shared.base_adapter import ATSAdapterBase

log = logging.getLogger(__name__)

class SmartRecruitersAdapter(ATSAdapterBase):
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Fetch jobs directly from SmartRecruiters API.
        """
        board_token = self.company_config.get("board_token", "")
        url = f"https://api.smartrecruiters.com/v1/companies/{board_token}/postings"
        
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                for item in data.get("content", []):
                    job_title = item.get("name", "")
                    
                    if query and query.lower() not in job_title.lower():
                        continue
                        
                    loc_obj = item.get("location", {})
                    job_location = f"{loc_obj.get('city', '')}, {loc_obj.get('region', '')}, {loc_obj.get('country', '')}".strip(", ")
                    
                    if location and location.lower() not in job_location.lower():
                        if location.lower() != "remote" or "remote" not in str(loc_obj.get('remote', '')).lower():
                            continue
                            
                    job_url = f"https://careers.smartrecruiters.com/{board_token}/{item.get('id')}"
                    posted_date = item.get("releasedDate", "")
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company_name,
                        "location": job_location,
                        "description": "", # Description requires a separate API call in SR
                        "url": job_url,
                        "apply_url": job_url,
                        "source": "smartrecruiters",
                        "posted_date": posted_date,
                        "job_type": item.get("typeOfEmployment", {}).get("label", "full-time"), 
                        "salary": "",
                        "source_priority": self.priority,
                        "company_tags": self._format_tags(),
                        "company_type": self.company_type
                    })
                    
        except Exception as e:
            log.warning(f"Failed to scrape SmartRecruiters for {self.company_name}: {e}")
            
        return jobs
