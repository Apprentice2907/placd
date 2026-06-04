import asyncio
from datetime import datetime
from typing import List
from urllib.parse import quote_plus
import structlog
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeout

from schemas.job import JobData

logger = structlog.get_logger(__name__)

class LinkedInScraper:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.request_count = 0
        
    async def search_jobs(self, query: str, location: str = '', limit: int = 100) -> List[JobData]:
        """Search LinkedIn jobs with scrolling."""
        jobs_list = []
        page = await self.context.new_page()
        
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location)
        url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"
        
        logger.info("linkedin_search_started", query=query, location=location)
        
        try:
            await page.goto(url, wait_until="networkidle")
            self.request_count += 1
            
            # Wait for job cards to appear
            try:
                await page.wait_for_selector("ul.jobs-search__results-list > li", timeout=10000)
            except PlaywrightTimeout:
                logger.warning("linkedin_no_results_found", url=url)
                return []
                
            # Scroll and extract
            previous_count = 0
            while len(jobs_list) < limit:
                cards = await page.locator("ul.jobs-search__results-list > li").all()
                if not cards or len(cards) == previous_count:
                    # Try clicking "See more jobs" if it exists
                    see_more = page.locator("button.infinite-scroller__show-more-button:visible")
                    if await see_more.count() > 0:
                        await see_more.click()
                        self.request_count += 1
                        await asyncio.sleep(2) # wait for load
                        continue
                    else:
                        # Scroll down
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        cards = await page.locator("ul.jobs-search__results-list > li").all()
                        if len(cards) == previous_count:
                            break # No more jobs loading
                            
                previous_count = len(cards)
                
                # We extract the ones we haven't processed yet
                for i in range(len(jobs_list), len(cards)):
                    if len(jobs_list) >= limit:
                        break
                        
                    card = cards[i]
                    
                    try:
                        title_el = card.locator("h3.base-search-card__title")
                        company_el = card.locator("h4.base-search-card__subtitle")
                        location_el = card.locator("span.job-search-card__location")
                        link_el = card.locator("a.base-card__full-link")
                        
                        title = await title_el.inner_text() if await title_el.count() else ""
                        company = await company_el.inner_text() if await company_el.count() else ""
                        loc = await location_el.inner_text() if await location_el.count() else ""
                        apply_url = await link_el.get_attribute("href") if await link_el.count() else ""
                        
                        if not title or not apply_url:
                            continue
                            
                        # Strip query params from URL for cleaner ID
                        clean_url = apply_url.split("?")[0]
                        job_id = clean_url.split("-")[-1] if "-" in clean_url else clean_url
                        
                        title_lower = title.lower()
                        is_remote = "remote" in loc.lower() or "remote" in title_lower
                        job_type = "internship" if "intern" in title_lower else "fulltime"
                        
                        jobs_list.append(JobData(
                            external_id=job_id,
                            title=title.strip(),
                            description="", # To get desc, we'd have to click the card and wait for the detail pane, skipping for bulk search performance unless specifically requested
                            apply_url=clean_url,
                            source="linkedin",
                            job_type=job_type,
                            location=loc.strip(),
                            is_remote=is_remote,
                            company_slug=company.strip().lower().replace(" ", "-"),
                            company_name=company.strip(),
                            scraped_at=datetime.utcnow()
                        ))
                    except Exception as e:
                        logger.debug("linkedin_card_extract_error", error=str(e))
                        
        except Exception as e:
            logger.error("linkedin_search_error", error=str(e))
        finally:
            await page.close()
            
        return jobs_list

    async def get_company_jobs(self, company_slug: str) -> List[JobData]:
        """Fetch jobs directly from a LinkedIn company page."""
        jobs_list = []
        page = await self.context.new_page()
        url = f"https://www.linkedin.com/company/{company_slug}/jobs/"
        
        try:
            await page.goto(url, wait_until="networkidle")
            self.request_count += 1
            
            try:
                # This depends heavily on whether the session is logged in.
                # Public company pages have different layouts.
                await page.wait_for_selector(".org-jobs-recently-posted-jobs-module__show-all-jobs-btn, a[data-tracking-control-name='org_workspace_jobs_see_all']", timeout=5000)
                see_all_btn = page.locator(".org-jobs-recently-posted-jobs-module__show-all-jobs-btn, a[data-tracking-control-name='org_workspace_jobs_see_all']").first
                if await see_all_btn.count() > 0:
                    search_url = await see_all_btn.get_attribute("href")
                    if search_url:
                        # Redirect to the actual search page for this company
                        if not search_url.startswith("http"):
                            search_url = f"https://www.linkedin.com{search_url}"
                        await page.close()
                        # We would essentially run the logic from search_jobs here on the new URL
                        # For simplicity, returning empty here to signify it needs the search_jobs method
                        logger.info("linkedin_company_redirects_to_search", search_url=search_url)
            except PlaywrightTimeout:
                pass
                
        except Exception as e:
            logger.error("linkedin_company_error", slug=company_slug, error=str(e))
        finally:
            if not page.is_closed():
                await page.close()
                
        return jobs_list
