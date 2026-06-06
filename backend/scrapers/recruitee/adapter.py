import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from scrapers.shared.base_adapter import UnifiedAdapter
from discovery.seed_lists import RECRUITEE_COMPANIES

log = logging.getLogger(__name__)

class RecruiteeAdapter(UnifiedAdapter):
    source = "recruitee"
    rpm = 30
    api_domain = "recruitee.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        all_jobs = []
        boards = []
        
        if getattr(self, 'board_token', None):
            boards = [{"name": self.company, "board_token": self.board_token}]
        elif getattr(self, 'company', None) and self.company != "Recruitee":
            boards = [{"name": self.company, "board_token": self.company.lower()}]
        else:
            log.info("Fetching all Recruitee boards from seed lists...")
            for slug in RECRUITEE_COMPANIES:
                boards.append({
                    "name": slug.title(),
                    "board_token": slug
                })
                
        log.info(f"Discovered {len(boards)} Recruitee boards. Beginning extraction...")
        semaphore = asyncio.Semaphore(50)
        
        async def fetch_board(board):
            slug = board.get("board_token")
            company_name = board.get("name") or slug
            url = f"https://{slug}.recruitee.com/api/offers"
            jobs = []
            
            async with self.get_client() as client:
                async with semaphore:
                    try:
                        resp = await self._fetch_with_retry(client, url)
                        if resp.status_code != 200:
                            return []
                            
                        data = resp.json()
                        for offer in data.get("offers", []):
                            title = offer.get("title", "")

                            location = offer.get("location", "")
                            is_remote = offer.get("remote", False)
                            if not location and is_remote:
                                location = "Remote"
                            if isinstance(location, str) and "remote" in location.lower():
                                is_remote = True

                            job_type = self._normalize_job_type(
                                offer.get("employment_type_code", ""),
                                title,
                            )

                            tags = offer.get("tags", [])
                            if not isinstance(tags, list):
                                tags = []

                            description = offer.get("description", "") or title

                            offer_slug = offer.get("slug", offer.get("id", ""))
                            apply_url = f"https://{slug}.recruitee.com/o/{offer_slug}"

                            salary_min = offer.get("min_salary") or offer.get("salary_min")
                            salary_max = offer.get("max_salary") or offer.get("salary_max")
                            salary_currency = offer.get("salary_currency", "USD")

                            jobs.append({
                                "title": title,
                                "company": company_name,
                                "location": location,
                                "description": description,
                                "apply_url": apply_url,
                                "url": apply_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": job_type,
                                "department": offer.get("department", "General"),
                                "date_posted": offer.get("created_at", datetime.now().isoformat()),
                                "is_remote": is_remote,
                                "is_hybrid": False,
                                "trust_score": 70,
                                "company_domain": f"{slug}.com",
                                "company_logo_url": None,
                                "company_tier": 3,
                                "skills": tags,
                                "salary_min": self._safe_int(salary_min),
                                "salary_max": self._safe_int(salary_max),
                                "salary_currency": salary_currency if self._safe_int(salary_min) else None,
                            })
                    except Exception as e:
                        log.debug(f"Failed to fetch Recruitee jobs for {slug}: {e}")
                        
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

    def _safe_int(self, val) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

if __name__ == "__main__":
    adapter = RecruiteeAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
