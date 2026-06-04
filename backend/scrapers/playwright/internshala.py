import asyncio
from datetime import datetime
from typing import List
import structlog
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeout

from schemas.job import JobData

logger = structlog.get_logger(__name__)

class IntershalaScraper:
    def __init__(self, context: BrowserContext):
        self.context = context
        
    async def search_internships(self, query: str = '', location: str = '') -> List[JobData]:
        """Search internships on Internshala using Playwright."""
        jobs_list = []
        page = await self.context.new_page()
        
        query_slug = query.lower().replace(" ", "-") if query else ""
        loc_slug = location.lower().replace(" ", "-") if location else ""
        
        path_parts = []
        if query_slug:
            path_parts.append(f"{query_slug}-internship")
        if loc_slug:
            path_parts.append(f"in-{loc_slug}")
            
        url_path = "/".join(path_parts) if path_parts else "internships"
        url = f"https://internshala.com/{url_path}"
        
        logger.info("internshala_search_started", url=url)
        
        try:
            await page.goto(url, wait_until="networkidle")
            
            try:
                await page.wait_for_selector(".individual_internship", timeout=10000)
            except PlaywrightTimeout:
                logger.warning("internshala_no_results", url=url)
                return []
                
            # Scroll to load more
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)
                
            cards = await page.locator(".individual_internship").all()
            
            for card in cards:
                try:
                    title_el = card.locator(".heading_4_5.profile")
                    company_el = card.locator(".heading_6.company_name")
                    loc_el = card.locator("#location_names")
                    
                    title = await title_el.inner_text() if await title_el.count() else ""
                    company = await company_el.inner_text() if await company_el.count() else ""
                    location_text = await loc_el.inner_text() if await loc_el.count() else ""
                    
                    apply_link_el = card.locator("a.view_detail_button")
                    if await apply_link_el.count() == 0:
                        apply_link_el = card.locator(".heading_4_5.profile a")
                        
                    apply_url = await apply_link_el.get_attribute("href") if await apply_link_el.count() else ""
                    if apply_url and not apply_url.startswith("http"):
                        apply_url = f"https://internshala.com{apply_url}"
                        
                    if not title or not apply_url:
                        continue
                        
                    # Extract stipend
                    stipend_el = card.locator(".stipend")
                    stipend = await stipend_el.inner_text() if await stipend_el.count() else ""
                    
                    # Try extracting numeric from stipend
                    salary_min = None
                    if stipend:
                        import re
                        nums = re.findall(r'\d+', stipend.replace(",", ""))
                        if nums:
                            salary_min = int(nums[0])
                    
                    is_remote = "work from home" in location_text.lower()
                    job_id = apply_url.split("-")[-1] if "-" in apply_url else apply_url
                    
                    jobs_list.append(JobData(
                        external_id=job_id,
                        title=title.strip(),
                        description="", # Need detail page for desc
                        apply_url=apply_url,
                        source="internshala",
                        job_type="internship",
                        location=location_text.strip(),
                        is_remote=is_remote,
                        company_slug=company.strip().lower().replace(" ", "-"),
                        company_name=company.strip(),
                        raw_data={"stipend_raw": stipend},
                        scraped_at=datetime.utcnow()
                    ))
                    # Optionally inject stipend into the JobData if we added salary_min field 
                    # We will store it in raw_data to be safe according to standard schema
                    if salary_min:
                        jobs_list[-1].raw_data["salary_min"] = salary_min
                        
                except Exception as e:
                    logger.debug("internshala_card_error", error=str(e))
                    
        except Exception as e:
            logger.error("internshala_search_error", error=str(e))
        finally:
            await page.close()
            
        return jobs_list
