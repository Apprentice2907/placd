from datetime import datetime
from typing import List
import httpx
import structlog
import asyncio

from .base import BaseCrawler, JobData

logger = structlog.get_logger(__name__)

class WorkableCrawler(BaseCrawler):
    
    async def crawl_company(self, subdomain: str) -> List[JobData]:
        """Fetch all jobs for a Workable company subdomain."""
        jobs_list = []
        url = f"https://apply.workable.com/api/v3/accounts/{subdomain}/jobs"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self.check_rate_limit("apply.workable.com", max_requests=10, window_seconds=1)
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                raw_jobs = data.get("results", [])
                
                for rj in raw_jobs:
                    title = rj.get("title", "")
                    title_lower = title.lower()
                    
                    location_dict = rj.get("location", {})
                    location = f"{location_dict.get('city', '')}, {location_dict.get('countryName', '')}".strip(", ")
                    
                    is_remote = rj.get("remote", False) or "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    apply_url = f"https://apply.workable.com/{subdomain}/j/{rj.get('shortcode')}"
                    
                    job_data = JobData(
                        external_id=str(rj.get("id", rj.get('shortcode'))),
                        title=title,
                        description=rj.get("description", ""),  # Workable search API might not return full desc
                        apply_url=apply_url,
                        source="workable",
                        job_type=job_type,
                        location=location,
                        is_remote=is_remote,
                        company_slug=subdomain,
                        company_name=subdomain.title(),
                        raw_data=rj,
                        scraped_at=datetime.utcnow()
                    )
                    jobs_list.append(job_data)
                    
            except Exception as e:
                logger.error("workable_crawl_error", subdomain=subdomain, error=str(e))
                    
        return jobs_list
