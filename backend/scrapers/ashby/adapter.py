import httpx
import logging
from bs4 import BeautifulSoup

from utils.config import REQUEST_TIMEOUT
from scrapers.shared.base_adapter import ATSAdapterBase

log = logging.getLogger(__name__)

class AshbyAdapter(ATSAdapterBase):
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Fetch jobs directly from Ashby API.
        """
        board_token = self.company_config.get("board_token", "")
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
        
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                for item in data.get("jobs", []):
                    job_title = item.get("title", "")
                    
                    if query and query.lower() not in job_title.lower():
                        continue
                        
                    job_location = item.get("location", "")
                    
                    if location and location.lower() not in job_location.lower():
                        if location.lower() != "remote" or "remote" not in job_location.lower():
                            continue
                            
                    job_url = item.get("jobUrl", "")
                    posted_date = item.get("publishedAt", "")
                    
                    description = item.get("descriptionHtml", "")
                    if description:
                        description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company_name,
                        "location": job_location,
                        "description": description,
                        "url": job_url,
                        "apply_url": item.get("applyUrl", job_url),
                        "source": "ashby",
                        "posted_date": posted_date,
                        "job_type": item.get("employmentType", "full-time"), 
                        "salary": "",
                        "source_priority": self.priority,
                        "company_tags": self._format_tags(),
                        "company_type": self.company_type
                    })
                    
        except Exception as e:
            log.warning(f"Failed to scrape Ashby for {self.company_name}: {e}")
            
        return jobs
