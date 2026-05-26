"""
Placd — Amazon Jobs Scraper
Uses the official Amazon Jobs JSON API (https://www.amazon.jobs/en/search.json).
Implements incremental scraping using `offset`.
"""
import logging
import httpx
from datetime import datetime

from utils.config import REQUEST_TIMEOUT
from db.database import get_scraping_state, save_scraping_state

log = logging.getLogger(__name__)

async def scrape_amazon_jobs(query: str, location: str = "") -> list[dict]:
    log.info(f"Scraping Amazon Jobs for '{query}' in '{location}'")
    jobs = []
    
    base_url = "https://www.amazon.jobs/en/search.json"
    
    # We will fetch up to 100 pages per scrape run to avoid rate limits while ingesting full dataset
    max_pages = 100
    limit = 100 # amazon default max limit usually 10-100, let's use 100 or rely on default
    
    # State tracking
    state = get_scraping_state("amazon_jobs")
    last_offset = state.get("offset", 0)
    last_query = state.get("query", "")
    
    # If query changed, reset offset
    if last_query != query:
        last_offset = 0
        
    current_offset = last_offset
    pages_fetched = 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        while pages_fetched < max_pages:
            params = {
                "query": query,
                "offset": current_offset,
                "result_limit": 100,
                "sort": "recent"
            }
            if location:
                params["location[]"] = location
                
            try:
                resp = await client.get(base_url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                job_items = data.get("jobs", [])
                if not job_items:
                    # No more jobs, reset offset
                    current_offset = 0
                    break
                    
                for j in job_items:
                    # Normalize fields
                    title = j.get("title", "")
                    job_path = j.get("job_path", "")
                    if not job_path:
                        continue
                        
                    full_url = f"https://www.amazon.jobs{job_path}"
                    apply_url = j.get("url_next_step", full_url)
                    
                    posted_date = j.get("posted_date", "")
                    
                    description = j.get("description", "")
                    basic_qual = j.get("basic_qualifications", "")
                    pref_qual = j.get("preferred_qualifications", "")
                    full_desc = f"{description}\n\nBasic Qualifications:\n{basic_qual}\n\nPreferred Qualifications:\n{pref_qual}"
                    
                    is_intern = 1 if j.get("is_intern") else 0
                    
                    jobs.append({
                        "title": title,
                        "company": "Amazon",
                        "location": j.get("location", ""),
                        "description": full_desc,
                        "url": full_url,
                        "apply_url": apply_url,
                        "source": "amazon_jobs",
                        "posted_date": posted_date,
                        "job_type": j.get("job_schedule_type", "full-time"),
                        "external_job_id": j.get("id_icims") or j.get("id"),
                        "source_priority": 10,
                        "company_tags": "FAANG, BigTech",
                        "company_type": "faang",
                        "is_internship": is_intern
                    })
                    
                current_offset += len(job_items)
                pages_fetched += 1
                
            except Exception as e:
                log.warning(f"Amazon Jobs API error at offset {current_offset}: {e}")
                break
                
    # Save next cursor
    save_scraping_state("amazon_jobs", {"offset": current_offset, "query": query})
    return jobs
