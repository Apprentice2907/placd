import logging
import urllib.parse
from bs4 import BeautifulSoup
import asyncio

log = logging.getLogger(__name__)

async def scrape_wellfound(query: str = "", location: str = "") -> list[dict]:
    """
    Fetch jobs from Wellfound using Playwright.
    Navigates to the wellfound job search page. Cloudflare may still block headless.
    Gracefully returns empty list if blocked.
    """
    # Wellfound (formerly AngelList) URLs are tricky, they usually use roles/locations instead of strict query params
    # For a general search MVP, we'll try to hit their jobs page and search the DOM.
    url = "https://wellfound.com/jobs"
    
    jobs = []
    
    try:
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Go to Wellfound
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait to see if Cloudflare challenge appears or job list loads
            try:
                # Wait for main job listing container
                await page.wait_for_selector("[data-test='JobCard']", timeout=15000)
            except PwTimeout:
                log.warning("Wellfound: Job cards not found. Likely blocked by Cloudflare or login wall.")
                await browser.close()
                return jobs
                
            # Scroll to load
            for _ in range(2):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
            html = await page.content()
            await browser.close()
            
            soup = BeautifulSoup(html, "html.parser")
            job_cards = soup.select("[data-test='JobCard']")
            
            for card in job_cards:
                title_elem = card.select_one("h2")
                company_elem = card.select_one("h4") # Approx, varies
                url_elem = card.select_one("a[href*='/jobs/']")
                
                if not title_elem or not url_elem:
                    continue
                    
                job_title = title_elem.get_text(strip=True)
                job_url = "https://wellfound.com" + url_elem.get("href", "") if url_elem.get("href", "").startswith("/") else url_elem.get("href", "")
                company_name = company_elem.get_text(strip=True) if company_elem else "Startup"
                
                # We do basic keyword filtering here since the URL doesn't cleanly support search params without auth
                if query and query.lower() not in job_title.lower() and query.lower() not in company_name.lower():
                    continue
                
                jobs.append({
                    "title": job_title,
                    "company": company_name,
                    "location": "Remote", # Default for wellfound unless parsed deeply
                    "description": "", 
                    "url": job_url,
                    "apply_url": job_url,
                    "source": "wellfound",
                    "posted_date": "",
                    "job_type": "full-time",
                    "salary": "",
                    "source_priority": 8
                })
                
    except ImportError:
        log.warning("Playwright not installed. Skipping Wellfound scrape.")
    except Exception as e:
        log.warning(f"Failed to scrape Wellfound via Playwright: {e}")
        
    return jobs
