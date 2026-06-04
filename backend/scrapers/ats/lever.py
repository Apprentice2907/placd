import asyncio
from datetime import datetime
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter

class LeverCrawler(UnifiedAdapter):
    source = "lever"
    rpm = 60
    api_domain = "api.lever.co"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs for a Lever company slug."""
        jobs_list = []
        urls_to_try = [
            f"https://api.lever.co/v0/postings/{self.company}?mode=json",
            f"https://jobs.lever.co/{self.company}/json"
        ]
        
        async with self.get_client() as client:
            raw_jobs = None
            for url in urls_to_try:
                try:
                    response = await self._fetch_with_retry(client, url)
                    raw_jobs = response.json()
                    break # Success
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).debug(f"lever_url_failed url={url} error={e}")
            
            if not raw_jobs:
                import logging
                logging.getLogger(__name__).error(f"lever_crawl_error slug={self.company} error='All endpoints failed'")
                return []
                
            for rj in raw_jobs:
                title = rj.get("text", "")
                title_lower = title.lower()
                categories = rj.get("categories", {})
                location = categories.get("location", "")
                
                is_remote = "remote" in location.lower() or "remote" in title_lower
                job_type = "internship" if "intern" in title_lower else "fulltime"
                
                jobs_list.append({
                    "title": title,
                    "company": self.company.title(),
                    "location": location,
                    "description": rj.get("descriptionPlain", ""),
                    "url": rj.get("hostedUrl", ""),
                    "apply_url": rj.get("hostedUrl", ""),
                    "source": self.source,
                    "job_type": job_type,
                    "is_remote": is_remote,
                    "raw_data": rj
                })
                    
        return jobs_list

if __name__ == "__main__":
    adapter = LeverCrawler({"name": "netflix"})
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
