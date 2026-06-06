"""
Placd — Meta Careers Adapter
Uses Playwright to evaluate window.__initialData
"""
import logging
import json
from typing import List, Dict, Any
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class MetaAdapter(UnifiedAdapter):
    source = "meta_careers"
    company = "Meta"
    rpm = 10
    api_domain = "www.metacareers.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        base_url = "https://www.metacareers.com/careers/jobs/?is_leadership=0"
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = await context.new_page()
                
                for page_num in range(1, 10):
                    url = f"{base_url}&page={page_num}"
                    log.info(f"Navigating to {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait a bit for initialData to be populated if needed
                    await page.wait_for_timeout(2000)
                    
                    initial_data = await page.evaluate("() => window.__initialData")
                    
                    if not initial_data:
                        log.warning(f"No window.__initialData found on page {page_num}")
                        break
                        
                    def find_jobs_recursive(obj):
                        found = []
                        if isinstance(obj, dict):
                            if "job_title" in obj and "id" in obj:
                                found.append(obj)
                            for v in obj.values():
                                found.extend(find_jobs_recursive(v))
                        elif isinstance(obj, list):
                            for v in obj:
                                found.extend(find_jobs_recursive(v))
                        return found

                    page_jobs = find_jobs_recursive(initial_data)
                    if not page_jobs:
                        break

                    new_jobs = 0
                    for j in page_jobs:
                        job_id = j.get("id")
                        title = j.get("job_title") or j.get("title", "")
                        if not job_id or not title:
                            continue

                        apply_url = f"https://www.metacareers.com/jobs/{job_id}/"
                        
                        if any(existing['url'] == apply_url for existing in jobs):
                            continue
                            
                        locations = j.get("locations", [])
                        location = " / ".join(locations) if isinstance(locations, list) else str(locations)
                        
                        jobs.append({
                            "title": title,
                            "company": self.company,
                            "location": location or "Global",
                            "description": j.get("job_description") or j.get("summary") or title,
                            "apply_url": apply_url,
                            "url": apply_url,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": "full_time",
                            "department": "Engineering",
                            "date_posted": datetime.now().isoformat(),
                            "is_remote": "remote" in location.lower(),
                            "is_hybrid": False,
                            "trust_score": 100,
                            "company_domain": "meta.com",
                            "company_logo_url": None,
                            "company_tier": 1,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None,
                        })
                        new_jobs += 1
                        
                    if new_jobs == 0:
                        break
                        
                await browser.close()
                
        except ImportError:
            log.warning("Playwright not installed.")
        except Exception as e:
            log.error(f"Failed to scrape Meta Careers via evaluate: {e}")
            
        return jobs

if __name__ == "__main__":
    import asyncio
    adapter = MetaAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
