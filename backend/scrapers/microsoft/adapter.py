"""
Placd — Microsoft Careers Scraper
Uses the official Microsoft Careers JSON API.
Implements incremental scraping using `start`.
"""
import logging
import httpx
from datetime import datetime

from utils.config import REQUEST_TIMEOUT
from db.database import get_scraping_state, save_scraping_state

log = logging.getLogger(__name__)

async def scrape_microsoft_careers(query: str, location: str = "") -> list[dict]:
    log.info(f"Scraping Microsoft Careers for '{query}' in '{location}'")
    jobs = []
    
    search_url = "https://apply.careers.microsoft.com/api/pcsx/search"
    details_url = "https://apply.careers.microsoft.com/api/pcsx/position_details"
    
    max_pages = 100
    page_size = 20
    
    state = get_scraping_state("microsoft_careers")
    last_offset = state.get("offset", 0)
    last_query = state.get("query", "")
    
    if last_query != query:
        last_offset = 0
        
    current_offset = last_offset
    pages_fetched = 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        while pages_fetched < max_pages:
            params = {
                "domain": "microsoft.com",
                "query": query,
                "start": current_offset
            }
            if location:
                params["location"] = location
                
            try:
                resp = await client.get(search_url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                positions = data.get("data", {}).get("positions", [])
                if not positions:
                    current_offset = 0
                    break
                    
                for p in positions:
                    title = p.get("name", "")
                    job_id = p.get("id")
                    
                    locs = p.get("locations", [])
                    job_location = locs[0] if locs else ""
                    
                    position_url = p.get("positionUrl", "")
                    full_url = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}" if job_id else ""
                    
                    # Microsoft search API doesn't include description. Fetch it using position_details.
                    description = ""
                    try:
                        det_resp = await client.get(details_url, params={"position_id": job_id, "domain": "microsoft.com", "hl": "en"}, headers=headers)
                        if det_resp.status_code == 200:
                            det_data = det_resp.json()
                            description = det_data.get("data", {}).get("description", "")
                    except Exception as e:
                        log.debug(f"Failed to fetch MSFT description for {job_id}: {e}")

                    posted_ts = p.get("postedTs")
                    posted_date = datetime.fromtimestamp(posted_ts).isoformat() if posted_ts else ""
                    
                    is_intern = 1 if "intern" in title.lower() else 0
                    
                    jobs.append({
                        "title": title,
                        "company": "Microsoft",
                        "location": job_location,
                        "description": description,
                        "url": full_url,
                        "apply_url": full_url,
                        "source": "microsoft_careers",
                        "posted_date": posted_date,
                        "job_type": p.get("workLocationOption", "onsite"),
                        "external_job_id": str(job_id),
                        "source_priority": 10,
                        "company_tags": "BigTech",
                        "company_type": "bigtech",
                        "is_internship": is_intern
                    })
                    
                current_offset += len(positions)
                pages_fetched += 1
                
            except Exception as e:
                log.warning(f"Microsoft Careers API error at offset {current_offset}: {e}")
                break
                
    save_scraping_state("microsoft_careers", {"offset": current_offset, "query": query})
    return jobs
