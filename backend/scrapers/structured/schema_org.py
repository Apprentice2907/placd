import asyncio
from typing import List
from datetime import datetime
import lxml.etree as ET
import httpx
import structlog
try:
    import extruct
except ImportError:
    extruct = None

from schemas.job import JobData
from scrapers.structured.base import StructuredBaseScraper

logger = structlog.get_logger(__name__)

class SchemaOrgScraper(StructuredBaseScraper):

    async def extract_jobs_from_url(self, url: str) -> List[JobData]:
        """Extract schema.org/JobPosting from a single URL."""
        if not extruct:
            logger.error("extruct_not_installed")
            return []
            
        try:
            response = await self.make_request("GET", url, headers={"Accept": "text/html,application/xhtml+xml"})
            html = response.text
            
            structured_data = extruct.extract(
                html, 
                base_url=url, 
                syntaxes=['json-ld', 'microdata', 'opengraph']
            )
            
            jobs = []
            
            # Helper to process an item
            def _process_item(item: dict):
                # Ensure it's a JobPosting
                item_type = item.get("@type", "")
                if isinstance(item_type, list):
                    if "JobPosting" not in item_type and "http://schema.org/JobPosting" not in item_type:
                        return
                elif item_type != "JobPosting" and item_type != "http://schema.org/JobPosting":
                    return
                    
                title = item.get("title", "")
                description = item.get("description", "")
                
                hiring_org = item.get("hiringOrganization", {})
                company_name = hiring_org.get("name", "") if isinstance(hiring_org, dict) else hiring_org
                
                job_loc = item.get("jobLocation", {})
                if isinstance(job_loc, list) and len(job_loc) > 0:
                    job_loc = job_loc[0]
                
                location = ""
                if isinstance(job_loc, dict):
                    address = job_loc.get("address", {})
                    if isinstance(address, dict):
                        parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
                        location = ", ".join([p for p in parts if p])
                        
                apply_url = item.get("url") or item.get("directApply") or url
                
                title_lower = title.lower()
                is_remote = "remote" in location.lower() or "remote" in title_lower
                job_type = "internship" if "intern" in title_lower else "fulltime"
                
                # generate ID
                external_id = apply_url.split("/")[-1] if "/" in apply_url else apply_url
                
                jobs.append(JobData(
                    external_id=external_id,
                    title=title,
                    description=description,
                    apply_url=apply_url,
                    source="schema_org",
                    job_type=job_type,
                    location=location,
                    is_remote=is_remote,
                    company_slug=company_name.replace(" ", "").lower(),
                    company_name=company_name,
                    raw_data=item,
                    scraped_at=datetime.utcnow()
                ))
            
            for item in structured_data.get("json-ld", []):
                if isinstance(item, dict):
                    # Sometimes wrapped in a graph
                    if "@graph" in item:
                        for g in item["@graph"]:
                            _process_item(g)
                    else:
                        _process_item(item)
                        
            for item in structured_data.get("microdata", []):
                _process_item(item)
                
            return jobs
            
        except Exception as e:
            logger.error("extract_jobs_failed", url=url, error=str(e))
            return []

    async def scan_sitemap(self, sitemap_url: str) -> List[str]:
        """Fetch a sitemap and extract jobs concurrently."""
        try:
            response = await self.make_request("GET", sitemap_url)
            root = ET.fromstring(response.content)
            
            # Extract all <loc>
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = root.findall(".//ns:url/ns:loc", namespaces=ns)
            if not locs:
                locs = root.findall(".//url/loc")
                
            job_urls = []
            for loc in locs:
                txt = loc.text
                if txt and any(kw in txt.lower() for kw in ["job", "career", "position"]):
                    job_urls.append(txt)
                    
            logger.info("sitemap_urls_found", url=sitemap_url, count=len(job_urls))
            
            semaphore = asyncio.Semaphore(10)
            all_jobs = []
            
            async def _process_url(job_url: str):
                async with semaphore:
                    return await self.extract_jobs_from_url(job_url)
                    
            tasks = [_process_url(u) for u in job_urls]
            for coro in asyncio.as_completed(tasks):
                jobs = await coro
                all_jobs.extend(jobs)
                
            return all_jobs
            
        except Exception as e:
            logger.error("scan_sitemap_failed", url=sitemap_url, error=str(e))
            return []
