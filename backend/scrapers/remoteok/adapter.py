import httpx
import logging
from bs4 import BeautifulSoup

from utils.config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

async def scrape_remoteok(query: str = "", location: str = "") -> list[dict]:
    """
    Fetch jobs from RemoteOK JSON API.
    API: https://remoteok.com/api
    """
    url = "https://remoteok.com/api"
    
    jobs = []
    try:
        headers = {
            "User-Agent": "Placd/1.0 (Contact: admin@placd.local)"
        }
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            # First item in RemoteOK API is usually a legal notice
            if data and isinstance(data, list):
                if "legal" in data[0]:
                    data = data[1:]
                    
            for item in data:
                job_title = item.get("position", "")
                
                if query and query.lower() not in job_title.lower() and query.lower() not in item.get("tags", []):
                    continue
                    
                job_location = item.get("location", "")
                
                # RemoteOK locations are messy ("Worldwide", "US Only", etc)
                if location and location.lower() != "remote":
                    if location.lower() not in job_location.lower():
                        continue
                        
                company_name = item.get("company", "")
                job_url = item.get("url", "")
                
                raw_html = item.get("description", "")
                description = ""
                if raw_html:
                    soup = BeautifulSoup(raw_html, "html.parser")
                    description = soup.get_text(separator="\n", strip=True)
                
                posted_date = item.get("date", "")
                
                jobs.append({
                    "title": job_title,
                    "company": company_name,
                    "location": job_location or "Remote",
                    "description": description,
                    "url": job_url,
                    "apply_url": item.get("apply_url", job_url),
                    "source": "remoteok",
                    "posted_date": posted_date,
                    "job_type": "full-time", # Default
                    "salary": str(item.get("salary_min", "")) + " - " + str(item.get("salary_max", "")),
                    "source_priority": 9
                })
                
    except Exception as e:
        log.warning(f"Failed to scrape RemoteOK: {e}")
        
    return jobs
