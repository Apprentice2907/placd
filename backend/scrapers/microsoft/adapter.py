"""
Placd — Microsoft Careers Scraper
Uses the official Microsoft Careers JSON API.
"""
import logging
from typing import List, Dict, Any
from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class MicrosoftAdapter(UnifiedAdapter):
    source = "microsoft_careers"
    company = "Microsoft"
    rpm = 30
    api_domain = "apply.careers.microsoft.com"

    MS_DISCIPLINES = [
        "Software Engineering", "Hardware Engineering",
        "Data Sciences", "Product Management",
        "IT Operations", "Security Engineering",
        "Cloud + Infrastructure", "Research, Applied, & Data Sciences",
        "Design & Creative", "Sales", "Finance", "Marketing",
    ]

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        client = self.get_client()
        jobs = []
        
        search_url = "https://apply.careers.microsoft.com/api/pcsx/search"
        details_url = "https://apply.careers.microsoft.com/api/pcsx/position_details"
        
        for discipline in self.MS_DISCIPLINES:
            current_offset = 0
            while True:
                params = {
                    "domain": "microsoft.com",
                    "query": discipline,
                    "start": current_offset
                }
                
                try:
                    resp = await self._fetch_with_retry(client, search_url, params=params)
                    data = resp.json()
                    
                    positions = data.get("data", {}).get("positions", [])
                    if not positions:
                        break
                        
                    for p in positions:
                        title = p.get("name", "")
                        job_id = p.get("id")
                        if not title or not job_id:
                            continue
                            
                        locs = p.get("locations", [])
                        job_location = locs[0] if locs else "Global"
                        
                        full_url = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"
                        
                        description = ""
                        try:
                            det_resp = await client.get(details_url, params={"position_id": job_id, "domain": "microsoft.com", "hl": "en"})
                            if det_resp.status_code == 200:
                                det_data = det_resp.json()
                                description = det_data.get("data", {}).get("description", "")
                        except Exception as e:
                            log.debug(f"Failed to fetch MSFT description for {job_id}: {e}")
                            
                        if not description:
                            description = title

                        posted_date = ""
                        posted_ts = p.get("postedTs")
                        if posted_ts:
                            from datetime import datetime
                            posted_date = datetime.fromtimestamp(posted_ts).isoformat()
                        
                        jobs.append({
                            "title": title,
                            "company": self.company,
                            "location": job_location,
                            "description": description,
                            "apply_url": full_url,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": p.get("workLocationOption", "full_time"),
                            "department": discipline,
                            "date_posted": posted_date,
                            "is_remote": "remote" in job_location.lower(),
                            "is_hybrid": False,
                            "trust_score": 100,
                            "company_domain": "microsoft.com",
                            "company_logo_url": None,
                            "company_tier": 1,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None,
                        })
                        
                    current_offset += len(positions)
                except Exception as e:
                    log.error(f"Microsoft Careers API error at discipline {discipline} offset {current_offset}: {e}")
                    break
                    
        return jobs

if __name__ == "__main__":
    import asyncio
    adapter = MicrosoftAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
