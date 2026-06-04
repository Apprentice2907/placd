import asyncio
from datetime import datetime
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter

class AshbyCrawler(UnifiedAdapter):
    source = "ashby"
    rpm = 60
    api_domain = "jobs.ashbyhq.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs for an Ashby company slug."""
        jobs_list = []
        url = f"https://jobs.ashbyhq.com/api/posting-api/job-board?organizationHostedJobsPageName={self.company}"
        
        async with self.get_client() as client:
            try:
                response = await self._fetch_with_retry(client, url)
                data = response.json()
                
                raw_jobs = data.get("jobPostings", [])
                
                for rj in raw_jobs:
                    title = rj.get("title", "")
                    title_lower = title.lower()
                    location = rj.get("locationName", "")
                    
                    is_remote = "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    jobs_list.append({
                        "title": title,
                        "company": self.company.title(),
                        "location": location,
                        "description": rj.get("descriptionHtml", ""),
                        "url": rj.get("externalLink", ""),
                        "apply_url": rj.get("externalLink", ""),
                        "source": self.source,
                        "job_type": job_type,
                        "is_remote": is_remote,
                        "raw_data": rj
                    })
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"ashby_crawl_error slug={self.company} error={e}")
                    
        return jobs_list

if __name__ == "__main__":
    adapter = AshbyCrawler({"name": "notion"})
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
