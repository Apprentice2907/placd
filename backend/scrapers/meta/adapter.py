"""
Placd — Meta Careers Adapter
Uses Playwright to render the page and extract jobs from the DOM (Tier 3 fallback).
"""
import logging
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime

from utils.config import USER_AGENT

log = logging.getLogger(__name__)

async def scrape_meta_careers(query: str, location: str = "") -> list[dict]:
    log.info(f"Scraping Meta Careers for '{query}' in '{location}'")
    jobs = []
    
    q = query.replace(" ", "%20")
    if q:
        base_url = f"https://www.metacareers.com/jobs/?q={q}"
    else:
        base_url = "https://www.metacareers.com/jobs/"
        
    try:
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            
            log.info(f"Navigating to {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            
            # Wait for job list
            try:
                await page.wait_for_selector("a[href*='/profile/job_details/']", timeout=10000)
            except PwTimeout:
                log.debug("Timeout waiting for Meta Careers specific selector. Continuing with snapshot.")
                
            for _ in range(50):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
            html = await page.content()
            await browser.close()
            
        soup = BeautifulSoup(html, "html.parser")
        
        links = soup.find_all("a", href=True)
        
        for a in links:
            href = a['href']
            # Meta jobs URLs look like /profile/job_details/123456789
            if "/profile/job_details/" in href:
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                    
                full_url = f"https://www.metacareers.com{href}" if href.startswith("/") else href
                
                parent = a.find_parent("div") or a.parent.parent
                desc = parent.get_text(separator=" ", strip=True) if parent else ""
                
                is_intern = 1 if "intern" in title.lower() or "intern" in desc.lower() else 0
                
                if any(j['url'] == full_url for j in jobs):
                    continue
                    
                job_id = href.strip("/").split("/")[-1]
                
                jobs.append({
                    "title": title,
                    "company": "Meta",
                    "location": location or "Global / Multiple",
                    "description": desc,
                    "url": full_url,
                    "apply_url": full_url,
                    "source": "meta_careers",
                    "posted_date": datetime.now().isoformat(),
                    "job_type": "full-time",
                    "external_job_id": job_id,
                    "source_priority": 10,
                    "company_tags": "FAANG, BigTech",
                    "company_type": "faang",
                    "is_internship": is_intern
                })
                
    except ImportError:
        log.warning("Playwright not installed. Meta Careers requires Playwright.")
    except Exception as e:
        log.warning(f"Failed to scrape Meta Careers: {e}")
        
    return jobs
