import asyncio
import logging
from bs4 import BeautifulSoup
from scrapers.shared.base_adapter import UnifiedAdapter
from discovery.seed_lists import ALL_SEED_LISTS

log = logging.getLogger(__name__)

class AshbyAdapter(UnifiedAdapter):
    source = "ashby"
    rpm = 60
    api_domain = "api.ashbyhq.com"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        boards = []
        
        if getattr(self, 'board_token', None):
            boards = [{"name": self.company, "board_token": self.board_token}]
        else:
            log.info("Fetching all Ashby boards from seed lists...")
            for seed_list in ALL_SEED_LISTS:
                for company_entry in seed_list:
                    if company_entry.get("ats_type") == "ashby" and company_entry.get("ats_slug"):
                        boards.append({
                            "name": company_entry.get("name"),
                            "board_token": company_entry.get("ats_slug")
                        })
                        
        log.info(f"Discovered {len(boards)} Ashby boards. Beginning extraction...")
        semaphore = asyncio.Semaphore(50)
        
        async def fetch_board(board):
            slug = board.get("board_token")
            company_name = board.get("name") or slug
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            jobs = []
            
            async with self.get_client() as client:
                async with semaphore:
                    try:
                        resp = await self._fetch_with_retry(client, url)
                        if resp.status_code != 200:
                            return []
                            
                        data = resp.json()
                        for item in data.get("jobs", []):
                            job_title = item.get("title", "")
                            job_location = item.get("location", "Global")
                            job_url = item.get("jobUrl", "")
                            posted_date = item.get("publishedAt", "")
                            department = item.get("department", "")
                            
                            description = item.get("descriptionHtml", "")
                            if description:
                                description = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)
                            if len(description) < 10:
                                description = job_title
                                
                            is_remote = "remote" in job_location.lower() or item.get("isRemote", False)
                            
                            jobs.append({
                                "title": job_title,
                                "company": company_name,
                                "location": job_location,
                                "description": description,
                                "apply_url": item.get("applyUrl", job_url),
                                "url": job_url,
                                "source": self.source,
                                "source_platform": self.source,
                                "job_type": item.get("employmentType", "full_time"), 
                                "department": department,
                                "date_posted": posted_date,
                                "is_remote": is_remote,
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
                        log.debug(f"Failed to fetch Ashby jobs for {slug}: {e}")
                        
            return jobs

        tasks = [fetch_board(board) for board in boards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)
                
        return all_jobs

if __name__ == "__main__":
    adapter = AshbyAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
