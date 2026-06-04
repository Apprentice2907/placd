import asyncio
from bs4 import BeautifulSoup
from scrapers.shared.base_adapter import UnifiedAdapter

class LeverAdapter(UnifiedAdapter):
    source = "lever"
    rpm = 60
    api_domain = "api.lever.co"

    async def fetch_jobs(self) -> list[dict]:
        url = f"https://api.lever.co/v0/postings/{self.board_token}?mode=json"
        jobs = []
        
        async with self.get_client() as client:
            resp = await self._fetch_with_retry(client, url)
            data = resp.json()
            
            for item in data:
                job_title = item.get("text", "")
                categories = item.get("categories", {})
                job_location = categories.get("location", "")
                job_url = item.get("hostedUrl", "")
                created_at = str(item.get("createdAt", ""))
                
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
                    "company": self.company,
                    "location": job_location,
                    "description": description,
                    "url": job_url,
                    "apply_url": item.get("applyUrl", job_url),
                    "source": self.source,
                    "posted_date": created_at,
                    "job_type": categories.get("commitment", "full-time"), 
                    "salary": "",
                    "source_priority": self.priority,
                    "company_tags": self._format_tags(),
                    "company_type": self.company_type
                })
                    
        return jobs

if __name__ == "__main__":
    adapter = LeverAdapter({"name": "Netflix", "board_token": "netflix"})
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
