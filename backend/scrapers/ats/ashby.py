from datetime import datetime
from typing import List
import httpx
import structlog
import asyncio

from .base import BaseCrawler, JobData

logger = structlog.get_logger(__name__)

class AshbyCrawler(BaseCrawler):
    
    async def crawl_company(self, slug: str) -> List[JobData]:
        """Fetch all jobs for an Ashby company slug."""
        jobs_list = []
        url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
        
        # Ashby generally uses GraphQL. If the user provided a REST endpoint in instructions:
        # url = f"https://jobs.ashby.com/api/posting-api/job-board?organizationHostedJobsPageName={slug}"
        # We will use the REST endpoint provided by the user's prompt.
        url = f"https://jobs.ashbyhq.com/api/posting-api/job-board?organizationHostedJobsPageName={slug}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self.check_rate_limit("jobs.ashbyhq.com", max_requests=10, window_seconds=1)
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                raw_jobs = data.get("jobPostings", [])
                
                for rj in raw_jobs:
                    title = rj.get("title", "")
                    title_lower = title.lower()
                    location = rj.get("locationName", "")
                    
                    is_remote = "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    job_data = JobData(
                        external_id=str(rj.get("id")),
                        title=title,
                        description=rj.get("descriptionHtml", ""),
                        apply_url=rj.get("externalLink", ""),
                        source="ashby",
                        job_type=job_type,
                        location=location,
                        is_remote=is_remote,
                        company_slug=slug,
                        company_name=slug.title(),
                        raw_data=rj,
                        scraped_at=datetime.utcnow()
                    )
                    jobs_list.append(job_data)
                    
            except Exception as e:
                logger.error("ashby_crawl_error", slug=slug, error=str(e))
                    
        return jobs_list
