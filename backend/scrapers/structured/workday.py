from typing import List
from datetime import datetime
import lxml.etree as ET
import httpx
import structlog

from scrapers.ats.base import JobData
from scrapers.structured.base import StructuredBaseScraper, RateLimitException

logger = structlog.get_logger(__name__)

class WorkdayScraper(StructuredBaseScraper):

    async def get_job_feed(self, company_domain: str) -> List[JobData]:
        """Fetch Workday jobs using sitemap (XML) first, fallback to API (JSON)."""
        jobs = []
        
        # Strategy 1: Sitemap
        try:
            jobs = await self._try_sitemap(company_domain)
            if jobs:
                return jobs
        except Exception as e:
            logger.debug("workday_sitemap_failed", domain=company_domain, error=str(e))
            
        # Strategy 2: API Pagination
        try:
            jobs = await self._try_api(company_domain)
            if jobs:
                return jobs
        except Exception as e:
            logger.warning("workday_api_failed", domain=company_domain, error=str(e))
            
        # Fallback
        logger.warning("workday_all_strategies_failed", domain=company_domain)
        await self.enqueue_playwright_fallback(company_domain)
        return []

    async def _try_sitemap(self, domain: str) -> List[JobData]:
        url = f"https://{domain}/feed/jobs"
        response = await self.make_request("GET", url)
        
        jobs = []
        try:
            # Parse XML
            root = ET.fromstring(response.content)
            # Find all <loc> inside <url> (handle namespaces if necessary)
            # Default namespace for sitemap is usually http://www.sitemaps.org/schemas/sitemap/0.9
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = root.findall(".//ns:url/ns:loc", namespaces=ns)
            
            # If no namespace
            if not locs:
                locs = root.findall(".//url/loc")
                
            for loc in locs:
                url_text = loc.text
                if url_text and ("/job/" in url_text or "/jobs/" in url_text):
                    # We only have URLs from sitemap, not full details.
                    # Usually sitemap Strategy is just to get URLs for Playwright or Extruct.
                    # But the prompt says "Parse <url><loc> entries" for Strategy 1. 
                    # If this is expected to return JobData, we create skeletal models.
                    slug = url_text.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()
                    jobs.append(JobData(
                        external_id=slug,
                        title=title,
                        description="", # Needs deeper scrape
                        apply_url=url_text,
                        source="workday",
                        job_type="fulltime",
                        location="",
                        is_remote=False,
                        company_slug=domain.split(".")[0],
                        company_name=domain.split(".")[0].title(),
                        scraped_at=datetime.utcnow()
                    ))
        except ET.XMLSyntaxError as e:
            logger.debug("workday_sitemap_xml_error", error=str(e))
            
        return jobs

    async def _try_api(self, domain: str) -> List[JobData]:
        # Domain example: company.wd1.myworkdayjobs.com
        parts = domain.split(".")
        if len(parts) < 3:
            return []
            
        company = parts[0]
        portal = "NVIDIAExternalCareerSite" # Need to discover this usually, or it's provided. 
        # Often it's just 'cxs/{company}/something/jobs'. For generic Workday, we might need 
        # to parse the portal from the homepage. But assuming we somehow know it or try a default.
        # The prompt says: POST https://{company}.wd1.myworkdayjobs.com/wday/cxs/{company}/{portal}/jobs
        # A common default portal is just the company name or 'External_Career_Site'
        portal = "External_Career_Site" 
        
        url = f"https://{company}.wd1.myworkdayjobs.com/wday/cxs/{company}/{portal}/jobs"
        
        limit = 20
        offset = 0
        jobs = []
        
        while True:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            try:
                response = await self.make_request("POST", url, json=payload, headers=headers)
                data = response.json()
                
                postings = data.get("jobPostings", [])
                if not postings:
                    break
                    
                for p in postings:
                    title = p.get("title", "")
                    location = p.get("locationsText", "")
                    title_lower = title.lower()
                    
                    is_remote = "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    external_path = p.get("externalPath", "")
                    apply_url = f"https://{domain}/en-US/{portal}{external_path}"
                    
                    jobs.append(JobData(
                        external_id=p.get("bulletinID", external_path.split("/")[-1]),
                        title=title,
                        description="", # Workday search API usually doesn't return full desc
                        apply_url=apply_url,
                        source="workday",
                        job_type=job_type,
                        location=location,
                        is_remote=is_remote,
                        company_slug=company,
                        company_name=company.title(),
                        raw_data=p,
                        scraped_at=datetime.utcnow()
                    ))
                    
                if len(postings) < limit:
                    break
                    
                offset += limit
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (404, 400):
                    # Portal might be wrong, would need discovery
                    logger.warning("workday_api_404_portal_likely_wrong", url=url)
                    break
                raise e
                
        return jobs
