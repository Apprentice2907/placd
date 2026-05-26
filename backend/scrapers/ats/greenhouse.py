import asyncio
from datetime import datetime
from typing import List, AsyncGenerator
import httpx
import structlog
from urllib.parse import urlencode

from .base import BaseCrawler, JobData

logger = structlog.get_logger(__name__)

class GreenhouseCrawler(BaseCrawler):
    
    async def crawl_company(self, slug: str) -> List[JobData]:
        """Fetch all jobs for a Greenhouse company slug."""
        jobs_list = []
        page = 1
        has_more = True
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while has_more:
                await self.check_rate_limit("boards-api.greenhouse.io", max_requests=10, window_seconds=1)
                
                url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true&page={page}"
                try:
                    response = await client.get(url)
                    response.raise_for_status()
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
                        
                        job_data = JobData(
                            external_id=str(rj.get("id")),
                            title=title,
                            description=rj.get("content", ""),
                            apply_url=rj.get("absolute_url", ""),
                            source="greenhouse",
                            job_type=job_type,
                            location=location,
                            is_remote=is_remote,
                            company_slug=slug,
                            company_name=data.get("name", slug),
                            raw_data=rj,
                            scraped_at=datetime.utcnow()
                        )
                        jobs_list.append(job_data)
                        
                    if len(raw_jobs) == 500:
                        page += 1
                    else:
                        has_more = False
                        
                except Exception as e:
                    logger.error("greenhouse_crawl_error", slug=slug, page=page, error=str(e))
                    break
                    
        return jobs_list
        
    async def crawl_all(self, company_slugs: List[str]) -> AsyncGenerator[JobData, None]:
        """Crawl multiple companies with concurrency limits."""
        semaphore = asyncio.Semaphore(20)
        count = 0
        
        async def _crawl(slug: str):
            async with semaphore:
                try:
                    return await self.crawl_company(slug)
                except Exception as e:
                    logger.error("greenhouse_crawl_all_error", slug=slug, error=str(e))
                    return []

        # We yield as soon as a company finishes
        for coro in asyncio.as_completed([_crawl(slug) for slug in company_slugs]):
            company_jobs = await coro
            for job in company_jobs:
                yield job
                
            count += 1
            if count % 100 == 0:
                logger.info("greenhouse_progress", companies_processed=count, total=len(company_slugs))
