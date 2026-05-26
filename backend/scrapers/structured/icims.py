from typing import List
from datetime import datetime
import lxml.etree as ET
import httpx
import structlog

from scrapers.ats.base import JobData
from scrapers.structured.base import StructuredBaseScraper

logger = structlog.get_logger(__name__)

class ICIMSScraper(StructuredBaseScraper):

    async def get_job_feed(self, customer_id: str, company_domain: str = None) -> List[JobData]:
        """Fetch jobs from iCIMS XML feeds."""
        urls_to_try = [f"https://careers-{customer_id}.icims.com/jobs/feed"]
        
        if company_domain:
            urls_to_try.extend([
                f"https://{company_domain}/careers/feed",
                f"https://{company_domain}/jobs/rss"
            ])
            
        for url in urls_to_try:
            try:
                response = await self.make_request("GET", url)
                jobs = self._parse_xml(response.content, customer_id)
                if jobs:
                    return jobs
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue
                logger.warning("icims_feed_error", url=url, status=e.response.status_code)
            except Exception as e:
                logger.debug("icims_xml_parse_error", url=url, error=str(e))
                
        logger.warning("icims_all_feeds_failed", customer_id=customer_id)
        return []

    def _parse_xml(self, content: bytes, customer_id: str) -> List[JobData]:
        jobs = []
        try:
            root = ET.fromstring(content)
            # Usually it's an RSS feed: <rss><channel><item>
            items = root.findall(".//item")
            
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                
                # iCIMS sometimes puts location in custom tags or within title/desc
                # For basic RSS:
                loc_elem = item.find("location") 
                
                title = title_elem.text if title_elem is not None else ""
                apply_url = link_elem.text if link_elem is not None else ""
                description = desc_elem.text if desc_elem is not None else ""
                location = loc_elem.text if loc_elem is not None else ""
                
                if not apply_url:
                    continue
                    
                title_lower = title.lower()
                is_remote = "remote" in location.lower() or "remote" in title_lower
                job_type = "internship" if "intern" in title_lower else "fulltime"
                
                # Try to extract an ID from the apply_url (e.g. .../jobs/1234/...)
                external_id = apply_url.split("/")[-1] if "/" in apply_url else apply_url
                
                jobs.append(JobData(
                    external_id=external_id,
                    title=title,
                    description=description,
                    apply_url=apply_url,
                    source="icims",
                    job_type=job_type,
                    location=location,
                    is_remote=is_remote,
                    company_slug=customer_id,
                    company_name=customer_id.title(),
                    scraped_at=datetime.utcnow()
                ))
        except ET.XMLSyntaxError:
            raise ValueError("Invalid XML content")
            
        return jobs
