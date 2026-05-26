import logging
import urllib.parse
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

async def scrape_linkedin(query: str = "", location: str = "Worldwide") -> list[dict]:
    """
    Fetch jobs from LinkedIn using Playwright to bypass 429 API blocks.
    Navigates to the guest search page, scrolls down, and parses HTML.
    """
    encoded_query = urllib.parse.quote(query)
    encoded_location = urllib.parse.quote(location)
    
    url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"
    
    jobs = []
    
    try:
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout
        
        async with async_playwright() as pw:
            # We use headed mode if possible, but fallback to headless. LinkedIn blocks headless Chrome heavily.
            # We use a standard user-agent string.
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Go to LinkedIn search page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for job cards to load (or fail gracefully if blocked)
            try:
                await page.wait_for_selector("ul.jobs-search__results-list, .jobs-search-results__list", timeout=10000)
            except PwTimeout:
                log.warning("LinkedIn: Job list selector not found or timed out. Possibly blocked.")
                await browser.close()
                return jobs
                
            # Scroll to load a few more jobs
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
            html = await page.content()
            await browser.close()
            
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            job_cards = soup.find_all("li")
            
            for card in job_cards:
                title_elem = card.find("h3", class_="base-search-card__title")
                company_elem = card.find("h4", class_="base-search-card__subtitle")
                location_elem = card.find("span", class_="job-search-card__location")
                url_elem = card.find("a", class_="base-card__full-link")
                date_elem = card.find("time", class_="job-search-card__listdate")
                
                if not title_elem or not url_elem:
                    continue
                    
                job_title = title_elem.get_text(strip=True)
                company_name = company_elem.get_text(strip=True) if company_elem else ""
                job_location = location_elem.get_text(strip=True) if location_elem else ""
                job_url = url_elem.get("href", "").split("?")[0] # Clean tracking params
                posted_date = date_elem.get("datetime", "") if date_elem else ""
                
                jobs.append({
                    "title": job_title,
                    "company": company_name,
                    "location": job_location,
                    "description": "", 
                    "url": job_url,
                    "apply_url": job_url,
                    "source": "linkedin",
                    "posted_date": posted_date,
                    "job_type": "full-time",
                    "salary": "",
                    "source_priority": 8
                })
                
    except ImportError:
        log.warning("Playwright not installed. Skipping LinkedIn scrape.")
    except Exception as e:
        log.warning(f"Failed to scrape LinkedIn via Playwright: {e}")
        
    return jobs
