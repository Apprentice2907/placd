"""
Placd — Google Careers Adapter
Uses httpx to parse HTML directly from the Google Careers page.
"""
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
import httpx
import re

from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class GoogleAdapter(UnifiedAdapter):
    source = "google_careers"
    company = "Google"
    rpm = 20
    api_domain = "careers.google.com"

    GOOGLE_CATEGORIES = [
        "Software Engineering",
        "Data Analytics",
        "Product Management",
        "Design",
        "Hardware Engineering"
    ]

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        base_url = "https://www.google.com/about/careers/applications/jobs/results"

        async with httpx.AsyncClient(timeout=30) as client:
            for category in self.GOOGLE_CATEGORIES:
                page = 1
                while page <= 5: # Limit to 5 pages per category to avoid long runs
                    params = {
                        "page": page,
                        "q": f'"{category}"'
                    }
                    
                    try:
                        resp = await client.get(base_url, params=params)
                        if resp.status_code != 200:
                            log.warning(f"Google returned {resp.status_code} for page {page}")
                            break
                            
                        html = resp.text
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Find all li tags containing a job
                        job_list = soup.find_all("li")
                        
                        found_on_page = 0
                        for li in job_list:
                            h3 = li.find("h3")
                            if not h3:
                                continue
                                
                            title = h3.text.strip()
                            if not title:
                                continue
                                
                            a = li.find("a", href=True)
                            if not a:
                                continue
                                
                            href = a["href"]
                            if "jobs/results/" not in href:
                                continue
                                
                            apply_url = f"https://www.google.com/about/careers/applications/{href.strip('../')}"
                            if any(existing['url'] == apply_url for existing in jobs):
                                continue
                                
                            # Extract location, which is usually in a div containing location icon text
                            location = "Global"
                            loc_elem = li.find(string=re.compile(r', \w+'))
                            if loc_elem:
                                location = loc_elem.strip()
                            elif li.find("span", class_="vo5Olc"):
                                location = li.find("span", class_="vo5Olc").text.strip()
                                
                            jobs.append({
                                "title": title,
                                "company": self.company,
                                "location": location,
                                "description": title, # HTML doesn't have full description, using title
                                "apply_url": apply_url,
                                "url": apply_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": "full_time",
                                "department": category,
                                "date_posted": datetime.now().isoformat(),
                                "is_remote": "remote" in location.lower(),
                                "is_hybrid": False,
                                "trust_score": 100,
                                "company_domain": "google.com",
                                "company_logo_url": None,
                                "company_tier": 1,
                                "skills": [],
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                            })
                            found_on_page += 1
                            
                        if found_on_page == 0:
                            break
                            
                        page += 1
                    except Exception as e:
                        log.error(f"Error fetching Google jobs: {e}")
                        break
                        
        return jobs

if __name__ == "__main__":
    import asyncio
    adapter = GoogleAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
