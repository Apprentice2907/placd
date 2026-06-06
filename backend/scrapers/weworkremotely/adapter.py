import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class WeWorkRemotelyAdapter(UnifiedAdapter):
    source = "weworkremotely"
    company = "WeWorkRemotely"
    rpm = 20
    api_domain = "weworkremotely.com"

    async def fetch_jobs(self) -> list[dict]:
        """
        Fetch jobs from WeWorkRemotely RSS feed.
        API: https://weworkremotely.com/remote-jobs.rss
        """
        url = "https://weworkremotely.com/remote-jobs.rss"
        jobs = []
        
        async with self.get_client() as client:
            try:
                resp = await self._fetch_with_retry(client, url)
                if resp.status_code != 200:
                    return jobs
                    
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
                        
                    job_location = "Remote"
                    
                    job_url = item.find("link").text if item.find("link") else ""
                    
                    raw_html = item.find("description").text if item.find("description") else ""
                    description = ""
                    if raw_html:
                        desc_soup = BeautifulSoup(raw_html, "html.parser")
                        description = desc_soup.get_text(separator="\n", strip=True)
                        
                    if not description:
                        description = job_title
                    
                    posted_date = item.find("pubDate").text if item.find("pubDate") else ""
                    
                    jobs.append({
                        "title": job_title,
                        "company": company_name,
                        "location": job_location,
                        "description": description,
                        "apply_url": job_url,
                        "url": job_url,
                        "source": self.source,
                        "source_platform": self.source,
                        "job_type": "full_time",
                        "department": "General",
                        "date_posted": posted_date,
                        "is_remote": True,
                        "is_hybrid": False,
                        "trust_score": 60,
                        "company_domain": "",
                        "company_logo_url": None,
                        "company_tier": 3,
                        "skills": [],
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": None,
                    })
                    
            except Exception as e:
                log.warning(f"Failed to scrape WeWorkRemotely: {e}")
                
        return jobs

if __name__ == "__main__":
    adapter = WeWorkRemotelyAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
