import httpx
import logging
from bs4 import BeautifulSoup

from utils.config import REQUEST_TIMEOUT
from scrapers.shared.base_adapter import ATSAdapterBase

log = logging.getLogger(__name__)

class GreenhouseAdapter(ATSAdapterBase):
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Fetch jobs directly from Greenhouse API.
        """
        board_token = self.company_config.get("board_token", "")
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        
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
                        
                    job_location = item.get("location", {}).get("name", "")
                    
                    if location and location.lower() not in job_location.lower():
                        if location.lower() != "remote" or "remote" not in job_location.lower():
                            continue
                            
                    job_url = item.get("absolute_url", "")
                    updated_at = item.get("updated_at", "")
                    
                    raw_html = item.get("content", "")
                    description = ""
                    if raw_html:
                        soup = BeautifulSoup(raw_html, "html.parser")
                        description = soup.get_text(separator="\n", strip=True)
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company_name,
                        "location": job_location,
                        "description": description,
                        "url": job_url,
                        "apply_url": job_url,
                        "source": "greenhouse",
                        "posted_date": updated_at,
                        "job_type": "full-time",
                        "salary": "",
                        "source_priority": self.priority,
                        "company_tags": self._format_tags(),
                        "company_type": self.company_type
                    })
                    
        except Exception as e:
            log.warning(f"Failed to scrape Greenhouse for {self.company_name}: {e}")
            
        return jobs
