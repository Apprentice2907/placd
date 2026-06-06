import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter
from discovery.seed_lists import BAMBOOHR_COMPANIES

log = logging.getLogger(__name__)

class BambooHRAdapter(UnifiedAdapter):
    source = "bamboohr"
    rpm = 30
    api_domain = "bamboohr.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        all_jobs = []
        boards = []
        
        if getattr(self, 'board_token', None):
            boards = [{"name": self.company, "board_token": self.board_token}]
        elif getattr(self, 'company', None) and self.company != "BambooHR":
            # the unified adapter might set self.company based on config, wait actually self.company is "BambooHR" by default.
            boards = [{"name": self.company, "board_token": self.company.lower()}]
        else:
            log.info("Fetching all BambooHR boards from seed lists...")
            for slug in BAMBOOHR_COMPANIES:
                boards.append({
                    "name": slug.title(),
                    "board_token": slug
                })
                
        log.info(f"Discovered {len(boards)} BambooHR boards. Beginning extraction...")
        semaphore = asyncio.Semaphore(50)
        
        async def fetch_board(board):
            slug = board.get("board_token")
            company_name = board.get("name") or slug
            url = f"https://{slug}.bamboohr.com/careers/list"
            jobs = []
            
            async with self.get_client() as client:
                async with semaphore:
                    try:
                        client.headers["Accept"] = "application/json"
                        resp = await self._fetch_with_retry(client, url)
                        if resp.status_code != 200:
                            return []
                            
                        data = resp.json()
                        for item in data.get("result", []):
                            title_obj = item.get("title", {})
                            title = title_obj.get("label", "") if isinstance(title_obj, dict) else str(title_obj)

                            loc_obj = item.get("location", {})
                            if isinstance(loc_obj, dict):
                                city = loc_obj.get("city", "")
                                country = loc_obj.get("country", "")
                                location = f"{city}, {country}".strip(", ") if city or country else ""
                            else:
                                location = str(loc_obj) if loc_obj else ""

                            is_remote = "remote" in location.lower() or "remote" in title.lower()

                            emp_obj = item.get("employmentType", {})
                            job_type_raw = emp_obj.get("label", "") if isinstance(emp_obj, dict) else str(emp_obj)
                            job_type = self._normalize_job_type(job_type_raw, title)

                            dept_obj = item.get("department", {})
                            department = dept_obj.get("label", "") if isinstance(dept_obj, dict) else str(dept_obj)

                            job_id = item.get("id", "")
                            apply_url = f"https://{slug}.bamboohr.com/careers/{job_id}"

                            description = item.get("description", "")
                            if isinstance(description, dict):
                                description = description.get("label", "")
                                
                            jobs.append({
                                "title": title,
                                "company": company_name,
                                "location": location or "Remote",
                                "description": description or title,
                                "apply_url": apply_url,
                                "url": apply_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": job_type,
                                "department": department,
                                "date_posted": datetime.now().isoformat(), # BambooHR public list doesn't provide dates easily
                                "is_remote": is_remote,
                                "is_hybrid": False,
                                "trust_score": 70,
                                "company_domain": f"{slug}.com",
                                "company_logo_url": None,
                                "company_tier": 3,
                                "skills": [],
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                            })
                    except Exception as e:
                        log.debug(f"Failed to fetch BambooHR jobs for {slug}: {e}")
                        
            return jobs

        tasks = [fetch_board(board) for board in boards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
                
        return all_jobs

    def _normalize_job_type(self, raw: str, title: str = "") -> str:
        raw_lower = (raw or "").lower()
        title_lower = (title or "").lower()
        if "intern" in raw_lower or "intern" in title_lower:
            return "internship"
        if "part" in raw_lower:
            return "part_time"
        if "contract" in raw_lower:
            return "contract"
        return "full_time"

if __name__ == "__main__":
    adapter = BambooHRAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
