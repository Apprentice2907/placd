"""
Placd — Naukri.com Scraper
Extends UnifiedAdapter. Sweeps keywords up to page 50.
"""
import logging
import asyncio
import random
from typing import List, Dict, Any
from datetime import datetime
from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class NaukriAdapter(UnifiedAdapter):
    source = "naukri"
    company = "Naukri"
    rpm = 20
    api_domain = "www.naukri.com"

    NAUKRI_KEYWORDS = [
        "software engineer", "backend developer", "frontend developer",
        "full stack developer", "python developer", "java developer",
        "react developer", "node.js developer", "data engineer",
        "data scientist", "machine learning engineer", "devops engineer",
        "android developer", "ios developer", "flutter developer",
        "cloud engineer", "aws engineer", "site reliability engineer",
        "product manager", "ui ux designer", "golang developer",
        "typescript developer", "kubernetes engineer", "security engineer",
        "blockchain developer", "embedded systems engineer",
    ]

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        
        headers = {
            "appid":           "109",
            "systemid":        "109",
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept":          "application/json, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer":         "https://www.naukri.com/",
        }

        try:
            import curl_cffi.requests as cfr
            session = cfr.AsyncSession(impersonate="chrome124", headers=headers, timeout=30.0)
        except ImportError:
            log.error("curl_cffi not available. Cannot scrape Naukri.")
            return jobs

        try:
            # Warm session
            await session.get("https://www.naukri.com/")
            
            for query in self.NAUKRI_KEYWORDS:
                for page in range(1, 21):
                    url = "https://www.naukri.com/jobapi/v3/search"
                    params = {
                        "keyword": query,
                        "location": "india",
                        "pageNo": page,
                        "noOfResults": 20,
                        "urlType": "search_by_keyword",
                        "searchType": "adv",
                    }
                    
                    try:
                        resp = await session.get(url, params=params)
                        if resp.status_code != 200:
                            log.warning(f"Naukri API error {resp.status_code} for {query} page {page}")
                            break
                            
                        data = resp.json()
                        raw_jobs = data.get("list", [])
                        
                        if not raw_jobs:
                            break
                            
                        for raw in raw_jobs:
                            title = (raw.get("post") or raw.get("jobSpec") or "").strip()
                            company_name = (raw.get("companyName") or "").strip()
                            if not title or not company_name:
                                continue
                                
                            job_url = (raw.get("urlStr") or "").split("?")[0].rstrip("/")
                            if not job_url:
                                job_id = str(raw.get("jobId", ""))
                                if job_id:
                                    job_url = f"https://www.naukri.com/job-listings-{job_id}"
                                else:
                                    continue
                                    
                            desc = raw.get("jobDesc") or raw.get("tupleDesc") or ""
                            
                            jobs.append({
                                "title": title,
                                "company": company_name,
                                "location": raw.get("city", "India"),
                                "description": desc if desc else title,
                                "apply_url": job_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": "full_time",
                                "department": "Engineering",
                                "date_posted": datetime.now().isoformat(),
                                "is_remote": False,
                                "is_hybrid": False,
                                "trust_score": 50,
                                "company_domain": "",
                                "company_logo_url": None,
                                "company_tier": 3,
                                "skills": [],
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                            })
                            
                        await asyncio.sleep(random.uniform(2.0, 5.0))
                    except Exception as e:
                        log.error(f"Error fetching Naukri jobs for {query} page {page}: {e}")
                        break
                        
        finally:
            await session.close()
            
        return jobs

if __name__ == "__main__":
    import asyncio
    adapter = NaukriAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
