import asyncio
from datetime import datetime
from typing import List, Dict, Any

from scrapers.shared.base_adapter import UnifiedAdapter

class WorkableCrawler(UnifiedAdapter):
    source = "workable"
    rpm = 60
    api_domain = "apply.workable.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all jobs for a Workable company subdomain."""
        jobs_list = []
        url = f"https://apply.workable.com/api/v3/accounts/{self.company}/jobs"
        
        async with self.get_client() as client:
            try:
                response = await self._fetch_with_retry(client, url)
                data = response.json()
                
                raw_jobs = data.get("results", [])
                
                for rj in raw_jobs:
                    title = rj.get("title", "")
                    title_lower = title.lower()
                    
                    location_dict = rj.get("location", {})
                    location = f"{location_dict.get('city', '')}, {location_dict.get('countryName', '')}".strip(", ")
                    
                    is_remote = rj.get("remote", False) or "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    apply_url = f"https://apply.workable.com/{self.company}/j/{rj.get('shortcode')}"
                    
                    jobs_list.append({
                        "title": title,
                        "company": self.company.title(),
                        "location": location,
                        "description": rj.get("description", ""),
                        "url": apply_url,
                        "apply_url": apply_url,
                        "source": self.source,
                        "job_type": job_type,
                        "is_remote": is_remote,
                        "raw_data": rj
                    })
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"workable_crawl_error slug={self.company} error={e}")
                    
        return jobs_list

if __name__ == "__main__":
    adapter = WorkableCrawler({"name": "revolut"})
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
