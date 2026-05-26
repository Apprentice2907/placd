import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime

from utils.config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

async def scrape_weworkremotely(query: str = "", location: str = "") -> list[dict]:
    """
    Fetch jobs from WeWorkRemotely RSS feed.
    API: https://weworkremotely.com/remote-jobs.rss
    """
    url = "https://weworkremotely.com/remote-jobs.rss"
    
    jobs = []
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")
            
            for item in items:
                # WWR Title format: "Company Name: Job Title"
                title_text = item.find("title").text if item.find("title") else ""
                
                company_name = ""
                job_title = title_text
                if ":" in title_text:
                    parts = title_text.split(":", 1)
                    company_name = parts[0].strip()
                    job_title = parts[1].strip()
                    
                if query and query.lower() not in job_title.lower() and query.lower() not in title_text.lower():
                    continue
                
                # Category often acts as location or job type
                job_location = "Remote"
                
                job_url = item.find("link").text if item.find("link") else ""
                
                raw_html = item.find("description").text if item.find("description") else ""
                description = ""
                if raw_html:
                    desc_soup = BeautifulSoup(raw_html, "html.parser")
                    description = desc_soup.get_text(separator="\n", strip=True)
                
                posted_date = item.find("pubDate").text if item.find("pubDate") else ""
                
                jobs.append({
                    "title": job_title,
                    "company": company_name,
                    "location": job_location,
                    "description": description,
                    "url": job_url,
                    "apply_url": job_url,
                    "source": "weworkremotely",
                    "posted_date": posted_date,
                    "job_type": "full-time",
                    "salary": "",
                    "source_priority": 9
                })
                
    except Exception as e:
        log.warning(f"Failed to scrape WeWorkRemotely: {e}")
        
    return jobs
