import asyncio
import random
import logging
import httpx
from bs4 import BeautifulSoup
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, is_valid_apply_url, extract_salary_from_text, parse_relative_date

log = logging.getLogger(__name__)
BASE_URL = "https://internshala.com"

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

class InternshalaAdapter(UnifiedAdapter):
    source = "internshala"
    rpm = 60
    api_domain = "internshala.com"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        semaphore = asyncio.Semaphore(5)
        detail_semaphore = asyncio.Semaphore(10)
        
        async with self.get_client() as client:
            client.headers.update(_DEFAULT_HEADERS)
            
            # 1. Fetch Internships (up to 50 pages)
            internship_url = f"{BASE_URL}/internships"
            internship_tasks = [
                self._fetch_search_page(client, internship_url, page, True, semaphore)
                for page in range(1, 51)
            ]
            
            # 2. Fetch Jobs (up to 100 pages)
            jobs_url = f"{BASE_URL}/jobs"
            job_tasks = [
                self._fetch_search_page(client, jobs_url, page, False, semaphore)
                for page in range(1, 101)
            ]
            
            # Run discovery
            log.info("Internshala: Discovering jobs & internships...")
            results = await asyncio.gather(*(internship_tasks + job_tasks), return_exceptions=True)
            
            discovered_jobs = []
            seen_urls = set()
            for res in results:
                if isinstance(res, list):
                    for job in res:
                        if job["url"] not in seen_urls:
                            seen_urls.add(job["url"])
                            discovered_jobs.append(job)
            
            log.info(f"Internshala: Discovered {len(discovered_jobs)} raw jobs. Fetching details...")
            
            # 3. Fetch details
            detail_tasks = [
                self._fetch_job_details(client, job, detail_semaphore)
                for job in discovered_jobs
            ]
            
            enriched_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            for res in enriched_results:
                if isinstance(res, dict) and res:
                    all_jobs.append(res)
                    
        return all_jobs

    async def _fetch_search_page(self, client: httpx.AsyncClient, base_url: str, page: int, is_internship: bool, semaphore: asyncio.Semaphore) -> list[dict]:
        page_url = f"{base_url}/page-{page}" if page > 1 else base_url
        jobs = []
        
        async with semaphore:
            try:
                resp = await self._fetch_with_retry(client, page_url)
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".individual_internship")
                
                if not cards:
                    return jobs
                    
                for card in cards:
                    url = ""
                    el = card.select_one(".view_detail_button") or card.select_one(".profile a[href*='/internship/'], .job-internship-name a")
                    if el and el.get("href"):
                        href = el["href"]
                        url = href if href.startswith("http") else f"{BASE_URL}{href}"
                        
                    if not url or not is_valid_apply_url(url):
                        continue
                        
                    title_el = card.select_one(".profile a, h3.heading_4_5 a, .job-internship-name a")
                    company_el = card.select_one(".company_name a, h4.heading_6 a, .company-name")
                    loc_el = card.select_one(".locations a, #location_names a, .location_link")
                    salary_el = card.select_one(".stipend, .desktop-text .stipend")
                    
                    is_wfh = False
                    if loc_el and ("work from home" in loc_el.get_text().lower() or "remote" in loc_el.get_text().lower()):
                        is_wfh = True

                    jobs.append({
                        "url": url.split("?")[0],
                        "apply_url": url.split("?")[0],
                        "title": title_el.get_text(strip=True) if title_el else "",
                        "company": company_el.get_text(strip=True) if company_el else "",
                        "location": loc_el.get_text(strip=True) if loc_el else "",
                        "salary": salary_el.get_text(strip=True) if salary_el else "",
                        "job_type": "internship" if is_internship else "full-time",
                        "is_remote": is_wfh,
                        "source": self.source,
                        "source_priority": 1,
                    })
                    
                await asyncio.sleep(1) # respectful delay
            except Exception as e:
                log.debug(f"Internshala search page error {page_url}: {e}")
                
        return jobs

    async def _fetch_job_details(self, client: httpx.AsyncClient, job: dict, semaphore: asyncio.Semaphore) -> dict:
        async with semaphore:
            try:
                resp = await self._fetch_with_retry(client, job["url"])
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Description
                desc_el = soup.select_one(".text-container, .job_description")
                if desc_el:
                    job["description"] = clean_description(desc_el.get_text(separator="\n"))
                else:
                    job["description"] = ""
                    
                # Skills
                skill_els = soup.select(".round_tabs")
                skills = [s.get_text(strip=True) for s in skill_els if s.get_text(strip=True)]
                job["skills"] = ", ".join(skills)
                
                # Applicants
                app_el = soup.select_one(".applications_message")
                if app_el:
                    import re
                    match = re.search(r'(\d+)', app_el.get_text())
                    if match:
                        job["applicants"] = int(match.group(1))
                        
                # Date posted (Internshala often says 'Posted 3 weeks ago' in a container)
                status_el = soup.select_one(".status-container .status")
                if status_el:
                    text = status_el.get_text(strip=True)
                    if "ago" in text.lower():
                        job["posted_date"] = parse_relative_date(text).isoformat()
                        
                # Salary extraction
                sal_min, sal_max, sal_curr = extract_salary_from_text(job["salary"])
                job["salary_min"] = sal_min
                job["salary_max"] = sal_max
                job["salary_currency"] = sal_curr
                
                # PPO flag
                if "ppo" in resp.text.lower() or "pre-placement offer" in resp.text.lower():
                    job["job_type"] += " (PPO possible)"
                    
                return job
            except Exception as e:
                log.debug(f"Internshala detail error {job['url']}: {e}")
                return {}

if __name__ == "__main__":
    adapter = InternshalaAdapter()
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
    if jobs:
        print(jobs[0])
