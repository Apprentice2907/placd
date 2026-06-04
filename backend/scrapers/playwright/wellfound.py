import asyncio
from datetime import datetime
from typing import List
from urllib.parse import quote_plus
import structlog
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeout

from schemas.job import JobData

logger = structlog.get_logger(__name__)

class WellfoundScraper:
    def __init__(self, context: BrowserContext):
        self.context = context
        
    async def search_jobs(self, query: str = 'software engineer', role_types: List[str] = ['Full time', 'Internship']) -> List[JobData]:
        """Search jobs on Wellfound (formerly AngelList)."""
        jobs_list = []
        page = await self.context.new_page()
        
        # Wellfound search URL structure
        # In reality, Wellfound heavily uses GraphQL and complex frontend routing.
        # Direct navigation to /role/software-engineer is common
        role_slug = query.lower().replace(" ", "-")
        url = f"https://wellfound.com/role/l/{role_slug}"
        
        logger.info("wellfound_search_started", query=query)
        
        try:
            await page.goto(url, wait_until="networkidle")
            
            # Wait for job cards
            try:
                await page.wait_for_selector("div[data-test='JobCard']", timeout=15000)
            except PlaywrightTimeout:
                logger.warning("wellfound_no_results", url=url)
                return []
                
            # Scroll down to load more
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
            cards = await page.locator("div[data-test='JobCard']").all()
            
            for card in cards:
                try:
                    title_el = card.locator("h2")
                    company_el = card.locator("h2").locator("xpath=../..//h1") # Extremely DOM dependent
                    # Fallbacks for wellfound specific classes if standard selectors fail
                    # Usually title is an <a> tag inside a header
                    title_link = card.locator("a.job-link").first
                    
                    if await title_link.count() > 0:
                        title = await title_link.inner_text()
                        apply_url = await title_link.get_attribute("href")
                        if apply_url and not apply_url.startswith("http"):
                            apply_url = f"https://wellfound.com{apply_url}"
                    else:
                        continue
                        
                    # Extract tags (location, salary, equity)
                    tags = await card.locator("span.styles_tag__").all_inner_texts()
                    location = ""
                    salary = ""
                    equity = ""
                    for tag in tags:
                        if "$" in tag:
                            salary = tag
                        elif "%" in tag:
                            equity = tag
                        elif not location:
                            location = tag # Assuming first non-monetary tag is location
                            
                    title_lower = title.lower()
                    is_remote = "remote" in location.lower() or "remote" in title_lower
                    job_type = "internship" if "intern" in title_lower else "fulltime"
                    
                    external_id = apply_url.split("/")[-1] if "/" in apply_url else apply_url
                    
                    jobs_list.append(JobData(
                        external_id=external_id,
                        title=title.strip(),
                        description="",
                        apply_url=apply_url,
                        source="wellfound",
                        job_type=job_type,
                        location=location.strip(),
                        is_remote=is_remote,
                        company_slug="",
                        company_name="", # Needs deeper DOM parsing to reliably get on Wellfound search cards
                        raw_data={"salary": salary, "equity": equity},
                        scraped_at=datetime.utcnow()
                    ))
                except Exception as e:
                    logger.debug("wellfound_card_error", error=str(e))
                    
        except Exception as e:
            logger.error("wellfound_search_error", error=str(e))
        finally:
            await page.close()
            
        return jobs_list
