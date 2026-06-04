import asyncio
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode

from scrapers.shared.base_adapter import UnifiedAdapter

class GreenhouseCrawler(UnifiedAdapter):
    source = "greenhouse"
    rpm = 60
    api_domain = "boards-api.greenhouse.io"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs for a Greenhouse company slug."""
        jobs_list = []
        page = 1
        has_more = True
        
        async with self.get_client() as client:
            while has_more:
                url = f"https://boards-api.greenhouse.io/v1/boards/{self.company}/jobs?content=true&page={page}"
                
                try:
                    response = await self._fetch_with_retry(client, url)
                    data = response.json()
                    
                    raw_jobs = data.get("jobs", [])
                    if not raw_jobs:
                        break
                        
                    for rj in raw_jobs:
                        title = rj.get("title", "")
                        title_lower = title.lower()
                        location = rj.get("location", {}).get("name", "")
                        
                        is_remote = "remote" in location.lower() or "remote" in title_lower
                        job_type = "internship" if "intern" in title_lower else "fulltime"
                        
                        jobs_list.append({
                            "title": title,
                            "company": data.get("name", self.company),
                            "location": location,
                            "description": rj.get("content", ""),
                            "url": rj.get("absolute_url", ""),
                            "apply_url": rj.get("absolute_url", ""),
                            "source": self.source,
                            "job_type": job_type,
                            "is_remote": is_remote,
                            "raw_data": rj
                        })
                        
                    if len(raw_jobs) == 500:
                        page += 1
                    else:
                        has_more = False
                        
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"greenhouse_crawl_error slug={self.company} page={page} error={e}")
                    break
                    
        return jobs_list

if __name__ == "__main__":
    adapter = GreenhouseCrawler({"name": "stripe", "board_token": "stripe"})
    # Need to override company with the slug from the config for consistency
    adapter.company = adapter.company_config.get("name", "stripe")
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
