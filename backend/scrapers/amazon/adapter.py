"""
Placd — Amazon Jobs Scraper
Uses the official Amazon Jobs JSON API (https://www.amazon.jobs/en/search.json).
"""
import logging
from typing import List, Dict, Any
from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class AmazonAdapter(UnifiedAdapter):
    source = "amazon_jobs"
    company = "Amazon"
    rpm = 30
    api_domain = "www.amazon.jobs"

    AMAZON_CATEGORIES = [
        "software-development", "systems-quality-assurance",
        "cloud-computing", "data-science", "machine-learning-science",
        "product-management", "solutions-architect",
        "technical-program-management", "security-and-compliance",
        "hardware-development", "network-development",
        "business-intelligence", "operations-it-and-support-engineering",
    ]

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        client = self.get_client()
        jobs = []
        base_url = "https://www.amazon.jobs/en/search.json"
        
        for category in self.AMAZON_CATEGORIES:
            offset = 0
            while True:
                params = {
                    "base_query": "",
                    "offset": str(offset),
                    "result_limit": "10",
                    "sort": "recent",
                    "category[]": category
                }
                
                try:
                    resp = await self._fetch_with_retry(client, base_url, params=params)
                    data = resp.json()
                    job_items = data.get("jobs", [])
                    
                    if not job_items:
                        break
                        
                    for j in job_items:
                        title = j.get("title", "")
                        job_path = j.get("job_path", "")
                        if not title or not job_path:
                            continue
                            
                        full_url = f"https://www.amazon.jobs{job_path}"
                        apply_url = j.get("url_next_step") or full_url
                        
                        description = j.get("description", "")
                        basic_qual = j.get("basic_qualifications", "")
                        pref_qual = j.get("preferred_qualifications", "")
                        full_desc = f"{description}\n\nBasic Qualifications:\n{basic_qual}\n\nPreferred Qualifications:\n{pref_qual}"
                        if len(full_desc) < 10:
                            full_desc = title
                            
                        jobs.append({
                            "title": title,
                            "company": self.company,
                            "location": j.get("location", "Global"),
                            "description": full_desc,
                            "apply_url": apply_url,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": j.get("job_schedule_type", "full_time"),
                            "department": category,
                            "date_posted": j.get("posted_date", ""),
                            "is_remote": "remote" in j.get("location", "").lower(),
                            "is_hybrid": False,
                            "trust_score": 100,
                            "company_domain": "amazon.com",
                            "company_logo_url": None,
                            "company_tier": 1,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None,
                        })
                        
                    offset += len(job_items)
                except Exception as e:
                    log.error(f"Amazon Jobs API error at category {category} offset {offset}: {e}")
                    break
                    
        return jobs

if __name__ == "__main__":
    import asyncio
    adapter = AmazonAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
