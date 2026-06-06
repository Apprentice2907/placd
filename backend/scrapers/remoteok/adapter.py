import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class RemoteOkAdapter(UnifiedAdapter):
    source = "remoteok"
    company = "RemoteOK"
    rpm = 20
    api_domain = "remoteok.com"

    async def fetch_jobs(self) -> list[dict]:
        url = "https://remoteok.com/api"
        jobs = []
        
        headers = {
            "User-Agent": "Placd/1.0 (Contact: admin@placd.local)"
        }
        
        async with self.get_client() as client:
            try:
                # the api is public, no specific pagination, just returns a list
                resp = await self._fetch_with_retry(client, url, headers=headers)
                if resp.status_code != 200:
                    return jobs
                    
                data = resp.json()
                
                if data and isinstance(data, list):
                    if "legal" in data[0]:
                        data = data[1:]
                        
                for item in data:
                    job_title = item.get("position", "")
                    company_name = item.get("company", "")
                    job_url = item.get("url", "")
                    job_location = item.get("location", "Remote")
                    
                    raw_html = item.get("description", "")
                    description = ""
                    if raw_html:
                        soup = BeautifulSoup(raw_html, "html.parser")
                        description = soup.get_text(separator="\n", strip=True)
                    
                    if not description:
                        description = job_title
                        
                    posted_date = item.get("date", "")
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    
                    jobs.append({
                        "title": job_title,
                        "company": company_name,
                        "location": job_location or "Remote",
                        "description": description,
                        "apply_url": item.get("apply_url", job_url) or job_url,
                        "url": job_url,
                        "source": self.source,
                        "source_platform": self.source,
                        "job_type": "full_time",
                        "department": "General",
                        "date_posted": posted_date or datetime.now().isoformat(),
                        "is_remote": True,
                        "is_hybrid": False,
                        "trust_score": 60,
                        "company_domain": "",
                        "company_logo_url": item.get("company_logo", ""),
                        "company_tier": 3,
                        "skills": item.get("tags", []),
                        "salary_min": salary_min if isinstance(salary_min, int) else None,
                        "salary_max": salary_max if isinstance(salary_max, int) else None,
                        "salary_currency": "USD",
                    })
            except Exception as e:
                log.warning(f"Failed to scrape RemoteOK: {e}")
                
        return jobs

if __name__ == "__main__":
    adapter = RemoteOkAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
