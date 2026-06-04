import asyncio
from bs4 import BeautifulSoup
from scrapers.shared.base_adapter import UnifiedAdapter

class AshbyAdapter(UnifiedAdapter):
    source = "ashby"
    rpm = 60
    api_domain = "api.ashbyhq.com"

    async def fetch_jobs(self) -> list[dict]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.board_token}"
        jobs = []
        
        async with self.get_client() as client:
            resp = await self._fetch_with_retry(client, url)
            data = resp.json()
            
            for item in data.get("jobs", []):
                job_title = item.get("title", "")
                job_location = item.get("location", "")
                job_url = item.get("jobUrl", "")
                posted_date = item.get("publishedAt", "")
                
                description = item.get("descriptionHtml", "")
                if description:
                    description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)
                
                jobs.append({
                    "title": job_title,
                    "company": self.company,
                    "location": job_location,
                    "description": description,
                    "url": job_url,
                    "apply_url": item.get("applyUrl", job_url),
                    "source": self.source,
                    "posted_date": posted_date,
                    "job_type": item.get("employmentType", "full-time"), 
                    "salary": "",
                    "source_priority": self.priority,
                    "company_tags": self._format_tags(),
                    "company_type": self.company_type
                })
                    
        return jobs

if __name__ == "__main__":
    adapter = AshbyAdapter({"name": "Notion", "board_token": "notion"})
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
