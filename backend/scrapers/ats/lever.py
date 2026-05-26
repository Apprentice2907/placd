from datetime import datetime
from typing import List
import httpx
import structlog
import asyncio

from .base import BaseCrawler, JobData

logger = structlog.get_logger(__name__)

class LeverCrawler(BaseCrawler):
    
    async def crawl_company(self, slug: str) -> List[JobData]:
        """Fetch all jobs for a Lever company slug."""
        jobs_list = []
        urls_to_try = [
            f"https://api.lever.co/v0/postings/{slug}?mode=json",
            f"https://jobs.lever.co/{slug}/json"
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            raw_jobs = None
            for url in urls_to_try:
                await self.check_rate_limit("api.lever.co", max_requests=10, window_seconds=1)
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    raw_jobs = response.json()
                    break # Success
                except Exception as e:
                    logger.debug("lever_url_failed", url=url, error=str(e))
            
            if not raw_jobs:
                logger.error("lever_crawl_error", slug=slug, error="All endpoints failed")
                return []
                
            for rj in raw_jobs:
                title = rj.get("text", "")
                title_lower = title.lower()
                categories = rj.get("categories", {})
                location = categories.get("location", "")
                
                is_remote = "remote" in location.lower() or "remote" in title_lower
                job_type = "internship" if "intern" in title_lower else "fulltime"
                
                job_data = JobData(
                    external_id=str(rj.get("id")),
                    title=title,
                    description=rj.get("descriptionPlain", ""),
                    apply_url=rj.get("hostedUrl", ""),
                    source="lever",
                    job_type=job_type,
                    location=location,
                    is_remote=is_remote,
                    company_slug=slug,
                    company_name=slug.title(),  # Lever JSON often doesn't contain company name at top level
                    raw_data=rj,
                    scraped_at=datetime.utcnow()
                )
                jobs_list.append(job_data)
                    
        return jobs_list
