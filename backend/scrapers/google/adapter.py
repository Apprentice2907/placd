"""
Placd — Google Careers Adapter
Uses Playwright to render the page and extract jobs from the DOM (Tier 3 fallback).
"""
import logging
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime

from utils.config import USER_AGENT
from db.database import get_scraping_state, save_scraping_state

log = logging.getLogger(__name__)

async def scrape_google_careers(query: str, location: str = "") -> list[dict]:
    log.info(f"Scraping Google Careers for '{query}' in '{location}'")
    jobs = []
    
    # Simple URL builder
    q = query.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    base_url = f"https://www.google.com/about/careers/applications/jobs/results/?q={q}"
    if loc:
        base_url += f"&location={loc}"
        
    try:
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            
            log.info(f"Navigating to {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=30000)
            
            try:
                # Wait for job results to load
                await page.wait_for_selector('a[href*="jobs/results/"]', timeout=10000) 
            except PwTimeout:
                log.debug("Timeout waiting for Google Careers specific selector.")
                
            # Scroll down to load more jobs (increased for full ingestion)
            for _ in range(50):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
            html = await page.content()
            await browser.close()
            
        soup = BeautifulSoup(html, "html.parser")
        
        links = soup.find_all("a", href=True)
        
        for a in links:
            href = a['href']
            # The href might be 'jobs/results/1234-role' or './jobs/results/...'
            if "jobs/results/" in href and "page=" not in href:
                title = a.get("aria-label", "")
                if not title:
                    title = a.get_text(strip=True)
                title = title.replace("Learn more about ", "")
                if not title or title.lower() in ("learn more", "apply", "share", "save", "job search"):
                    continue
                    
                # Clean up URL
                clean_href = href
                if clean_href.startswith("./"):
                    clean_href = clean_href[2:]
                elif clean_href.startswith("/"):
                    clean_href = clean_href[1:]
                    
                full_url = f"https://www.google.com/about/careers/applications/{clean_href}"
                
                # Extract job ID
                job_id = clean_href.split("?")[0].split("/")[-1]
                if not job_id or len(job_id) < 5:
                    continue
                
                parent = a.find_parent("li") or a.parent.parent
                desc = parent.get_text(separator=" ", strip=True) if parent else ""
                
                is_intern = 1 if "intern" in title.lower() or "intern" in desc.lower() else 0
                
                if any(j['url'] == full_url for j in jobs):
                    continue
                    
                jobs.append({
                    "title": title,
                    "company": "Google",
                    "location": location or "Global / Multiple",
                    "description": desc,
                    "url": full_url,
                    "apply_url": full_url,
                    "source": "google_careers",
                    "posted_date": datetime.now().isoformat(),
                    "job_type": "full-time",
                    "external_job_id": job_id,
                    "source_priority": 10,
                    "company_tags": "FAANG, BigTech",
                    "company_type": "faang",
                    "is_internship": is_intern
                })
                
    except ImportError:
        log.warning("Playwright not installed. Google Careers requires Playwright.")
    except Exception as e:
        log.warning(f"Failed to scrape Google Careers: {e}")
        
    return jobs
