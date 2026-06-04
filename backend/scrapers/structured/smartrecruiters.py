from typing import List
from datetime import datetime
import httpx
import structlog

from schemas.job import JobData
from scrapers.structured.base import StructuredBaseScraper

logger = structlog.get_logger(__name__)

class SmartRecruitersScraper(StructuredBaseScraper):

    async def get_jobs(self, company_id: str) -> List[JobData]:
        """Fetch all published jobs for a SmartRecruiters company ID."""
        jobs_list = []
        limit = 100
        offset = 0
        
        url_template = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
        
        while True:
            url = f"{url_template}?status=PUBLISHED&limit={limit}&offset={offset}"
            try:
                response = await self.make_request("GET", url, headers={"Accept": "application/json"})
                data = response.json()
                
                content = data.get("content", [])
                if not content:
                    break
                    
                for p in content:
                    title = p.get("name", "")
                    title_lower = title.lower()
                    
                    loc_dict = p.get("location", {})
                    location = f"{loc_dict.get('city', '')}, {loc_dict.get('region', '')}, {loc_dict.get('country', '')}".strip(", ")
                    
                    is_remote = loc_dict.get("remote", False) or "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    job_id = str(p.get("id"))
                    apply_url = f"https://jobs.smartrecruiters.com/{company_id}/{job_id}"
                    
                    jobs_list.append(JobData(
                        external_id=job_id,
                        title=title,
                        description="", # Detailed descriptions usually require a separate call per job on SR API
                        apply_url=apply_url,
                        source="smartrecruiters",
                        job_type=job_type,
                        location=location,
                        is_remote=is_remote,
                        company_slug=company_id,
                        company_name=company_id.title(),
                        raw_data=p,
                        scraped_at=datetime.utcnow()
                    ))
                    
                if len(content) < limit:
                    break
                    
                offset += limit
                
            except httpx.HTTPStatusError as e:
                logger.error("smartrecruiters_api_error", company_id=company_id, status=e.response.status_code)
                break
            except Exception as e:
                logger.error("smartrecruiters_crawl_error", company_id=company_id, error=str(e))
                break
                
        return jobs_list
