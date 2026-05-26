import httpx
import logging
from bs4 import BeautifulSoup

from utils.config import REQUEST_TIMEOUT
from scrapers.shared.base_adapter import ATSAdapterBase

log = logging.getLogger(__name__)

class LeverAdapter(ATSAdapterBase):
    async def scrape(self, query: str = "", location: str = "") -> list[dict]:
        """
        Fetch jobs directly from Lever API.
        """
        board_token = self.company_config.get("board_token", "")
        url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
        
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                for item in data:
                    job_title = item.get("text", "")
                    
                    if query and query.lower() not in job_title.lower():
                        continue
                        
                    categories = item.get("categories", {})
                    job_location = categories.get("location", "")
                    
                    if location and location.lower() not in job_location.lower():
                        if location.lower() != "remote" or "remote" not in categories.get("workplaceType", "").lower():
                            continue
                            
                    job_url = item.get("hostedUrl", "")
                    created_at = str(item.get("createdAt", ""))
                    
                    # Convert timestamp if needed
                    if created_at.isdigit():
                        from datetime import datetime
                        created_at = datetime.fromtimestamp(int(created_at) / 1000).isoformat()
                        
                    description = item.get("descriptionPlain", "")
                    if not description:
                        html_desc = item.get("description", "")
                        if html_desc:
                            description = BeautifulSoup(html_desc, "html.parser").get_text(separator="\n", strip=True)
                    
                    jobs.append({
                        "title": job_title,
                        "company": self.company_name,
                        "location": job_location,
                        "description": description,
                        "url": job_url,
                        "apply_url": item.get("applyUrl", job_url),
                        "source": "lever",
                        "posted_date": created_at,
                        "job_type": categories.get("commitment", "full-time"), 
                        "salary": "",
                        "source_priority": self.priority,
                        "company_tags": self._format_tags(),
                        "company_type": self.company_type
                    })
                    
        except Exception as e:
            log.warning(f"Failed to scrape Lever for {self.company_name}: {e}")
            
        return jobs
