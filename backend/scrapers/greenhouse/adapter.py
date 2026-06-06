import asyncio
import logging
from bs4 import BeautifulSoup
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, parse_relative_date

log = logging.getLogger(__name__)

class GreenhouseAdapter(UnifiedAdapter):
    source = "greenhouse"
    rpm = 300  # Higher limit for bulk
    api_domain = "boards-api.greenhouse.io"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        
        async with self.get_client() as client:
            # 1. Fetch company list dynamically if no specific board_token
            boards = []
            if getattr(self, 'board_token', None):
                boards = [{"board_token": self.board_token}]
            else:
                log.info("Fetching all public Greenhouse boards...")
                boards_url = "https://boards-api.greenhouse.io/v1/boards"
                try:
                    resp = await self._fetch_with_retry(client, boards_url)
                    data = resp.json()
                    boards = data if isinstance(data, list) else data.get("boards", [])
                except Exception as e:
                    log.error(f"Failed to fetch boards list: {e}")
                    return []

            log.info(f"Discovered {len(boards)} Greenhouse boards. Beginning extraction...")
            
            # 2. Process boards concurrently with Semaphore
            semaphore = asyncio.Semaphore(50)
            
            async def fetch_board(board):
                slug = board.get("board_token") or board.get("id")
                if not slug:
                    return []
                    
                url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
                jobs = []
                
                async with semaphore:
                    try:
                        resp = await self._fetch_with_retry(client, url)
                        # Detect dead boards
                        if resp.status_code in (404, 410):
                            log.debug(f"Dead board detected: {slug}")
                            return []
                            
                        data = resp.json()
                        job_list = data.get("jobs", [])
                        total = data.get("meta", {}).get("total", len(job_list))
                        if total == 0 and not job_list:
                            log.debug(f"Empty board detected: {slug}")
                            return []
                            
                        for item in job_list:
                            # Extract department & office
                            departments = item.get("departments", [])
                            department = departments[0].get("name", "") if departments else ""
                            
                            offices = item.get("offices", [])
                            office = offices[0].get("name", "") if offices else item.get("location", {}).get("name", "")
                            
                            job_title = item.get("title", "")
                            job_url = item.get("absolute_url", "")
                            updated_at = item.get("updated_at", "")
                            
                            raw_html = item.get("content", "")
                            description = clean_description(raw_html)
                            
                            if len(description) < 50:
                                continue
                                
                            jobs.append({
                                "title": job_title,
                                "company": self.company or slug,
                                "location": office,
                                "description": description,
                                "apply_url": job_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": "full_time",
                                "department": department,
                                "date_posted": parse_relative_date(updated_at).isoformat() if updated_at else None,
                                "is_remote": "remote" in office.lower() or "remote" in description.lower(),
                                "is_hybrid": False,
                                "trust_score": 80,
                                "company_domain": f"{slug}.com",
                                "company_logo_url": None,
                                "company_tier": 2,
                                "skills": [],
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                            })
                    except Exception as e:
                        # Log but don't fail the whole run
                        log.debug(f"Failed to fetch jobs for board {slug}: {e}")
                        
                return jobs

            tasks = [fetch_board(board) for board in boards]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, list):
                    all_jobs.extend(res)
                    
        return all_jobs

if __name__ == "__main__":
    adapter = GreenhouseAdapter({"name": "Stripe", "board_token": "stripe"})
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
