import os
import asyncio
import logging
from bs4 import BeautifulSoup
import httpx
from scrapers.shared.base_adapter import UnifiedAdapter
from scrapers.shared.utils import clean_description, is_valid_apply_url, parse_relative_date

log = logging.getLogger(__name__)

class WellfoundAdapter(UnifiedAdapter):
    source = "wellfound"
    rpm = 20
    api_domain = "wellfound.com"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        cookie = os.environ.get("WELLFOUND_SESSION_COOKIE")
        
        # Method 1: GraphQL (requires cookie)
        if cookie:
            log.info("Wellfound: Attempting GraphQL API with session cookie...")
            jobs = await self._scrape_graphql(cookie)
            if jobs:
                return jobs
            log.warning("Wellfound: GraphQL returned no jobs, falling back to RSS/Playwright")
            
        # Method 2: RSS fallback (not highly reliable globally, but good for specific companies if configured)
        if hasattr(self, 'company') and self.company:
            jobs = await self._scrape_rss()
            if jobs:
                return jobs
                
        # Method 3: Playwright Fallback
        log.info("Wellfound: Attempting Playwright fallback...")
        return await self._scrape_playwright()

    async def _scrape_graphql(self, cookie: str) -> list[dict]:
        jobs = []
        url = "https://wellfound.com/graphql"
        headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # A basic query for StartupJobListings
        payload = {
            "operationName": "StartupJobListings",
            "variables": {
                "locationNames": ["India", "Remote"]
            },
            "query": """
            query StartupJobListings($locationNames: [String!]) {
              talent {
                jobSearchResults(locationNames: $locationNames) {
                  jobs {
                    id
                    title
                    liveStartAt
                    jobType
                    remoteAllowed
                    description
                    compensation {
                      currencyCode
                      minSalary
                      maxSalary
                      minEquity
                      maxEquity
                    }
                    startup {
                      name
                      slug
                      companyStage
                      highConceptPitch
                      companySize
                      fundingAmount
                    }
                  }
                }
              }
            }
            """
        }
        
        async with self.get_client() as client:
            try:
                resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_jobs = data.get("data", {}).get("talent", {}).get("jobSearchResults", {}).get("jobs", [])
                    for job in raw_jobs:
                        startup = job.get("startup", {})
                        comp = job.get("compensation", {})
                        
                        slug = startup.get("slug", "")
                        job_id = job.get("id", "")
                        apply_url = f"https://wellfound.com/company/{slug}/jobs/{job_id}" if slug and job_id else ""
                        
                        min_equity = comp.get("minEquity")
                        max_equity = comp.get("maxEquity")
                        equity = ""
                        if min_equity is not None and max_equity is not None:
                            equity = f"{min_equity}% - {max_equity}%"
                            
                        jobs.append({
                            "title": job.get("title", ""),
                            "company": startup.get("name", ""),
                            "location": "Remote" if job.get("remoteAllowed") else "India",
                            "description": clean_description(job.get("description", "")),
                            "apply_url": apply_url,
                            "url": apply_url,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": job.get("jobType", "full_time"),
                            "department": "General",
                            "date_posted": parse_relative_date(job.get("liveStartAt", "")).isoformat() if job.get("liveStartAt") else None,
                            "is_remote": bool(job.get("remoteAllowed")),
                            "is_hybrid": False,
                            "trust_score": 70,
                            "company_domain": "",
                            "company_logo_url": None,
                            "company_tier": 3,
                            "skills": [],
                            "salary_min": int(comp.get("minSalary") or 0) or None,
                            "salary_max": int(comp.get("maxSalary") or 0) or None,
                            "salary_currency": comp.get("currencyCode", "USD") if comp.get("minSalary") else None,
                        })
            except Exception as e:
                log.error(f"Wellfound GraphQL error: {e}")
                
        return jobs

    async def _scrape_rss(self) -> list[dict]:
        # Typically https://wellfound.com/company/{slug}/jobs.rss
        jobs = []
        if not hasattr(self, 'company_config') or not self.company_config.get("slug"):
            return jobs
            
        slug = self.company_config.get("slug")
        url = f"https://wellfound.com/company/{slug}/jobs.rss"
        
        async with self.get_client() as client:
            try:
                resp = await self._fetch_with_retry(client, url)
                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.text)
                    for item in root.findall(".//item"):
                        title = item.findtext("title")
                        link = item.findtext("link")
                        desc = item.findtext("description")
                        pubDate = item.findtext("pubDate")
                        
                        jobs.append({
                            "title": title,
                            "company": self.company,
                            "location": "Remote",
                            "description": clean_description(desc),
                            "apply_url": link,
                            "url": link,
                            "source": self.source,
                            "source_platform": self.source,
                            "job_type": "full_time",
                            "department": "General",
                            "date_posted": parse_relative_date(pubDate).isoformat() if pubDate else None,
                            "is_remote": True,
                            "is_hybrid": False,
                            "trust_score": 70,
                            "company_domain": "",
                            "company_logo_url": None,
                            "company_tier": 3,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "salary_currency": None,
                        })
            except Exception as e:
                log.debug(f"Wellfound RSS failed for {slug}: {e}")
        return jobs

    async def _scrape_playwright(self) -> list[dict]:
        url = "https://wellfound.com/jobs"
        jobs = []
        
        try:
            from playwright.async_api import async_playwright, TimeoutError as PwTimeout
            import random
            
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                # Anti-bot: realistic user agent and viewport
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                
                # Navigate
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Random mouse movements to bypass basic cloudflare
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                
                try:
                    await page.wait_for_selector("[data-test='JobCard']", timeout=15000)
                except PwTimeout:
                    log.warning("Wellfound: Job cards not found. Blocked by Cloudflare or login wall.")
                    await browser.close()
                    return jobs
                    
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    
                html = await page.content()
                await browser.close()
                
                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select("[data-test='JobCard']")
                
                for card in job_cards:
                    title_elem = card.select_one("h2")
                    company_elem = card.select_one("h4")
                    url_elem = card.select_one("a[href*='/jobs/']")
                    
                    if not title_elem or not url_elem:
                        continue
                        
                    job_title = title_elem.get_text(strip=True)
                    job_url = "https://wellfound.com" + url_elem.get("href", "") if url_elem.get("href", "").startswith("/") else url_elem.get("href", "")
                    company_name = company_elem.get_text(strip=True) if company_elem else "Startup"
                    
                    # Optional: Look for equity in text
                    card_text = card.get_text()
                    import re
                    equity_match = re.search(r'([\d\.]+%[ \-]+[\d\.]+%)', card_text)
                    equity = equity_match.group(1) if equity_match else ""
                    
                    jobs.append({
                        "title": job_title,
                        "company": company_name,
                        "location": "Remote", 
                        "description": job_title, # Difficult to get full desc from cards alone
                        "apply_url": job_url,
                        "url": job_url,
                        "source": self.source,
                        "source_platform": self.source,
                        "job_type": "full_time",
                        "department": "General",
                        "date_posted": None,
                        "is_remote": True,
                        "is_hybrid": False,
                        "trust_score": 70,
                        "company_domain": "",
                        "company_logo_url": None,
                        "company_tier": 3,
                        "skills": [],
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": None,
                    })
                    
        except ImportError:
            log.warning("Playwright not installed. Skipping Wellfound Playwright scrape.")
        except Exception as e:
            log.warning(f"Failed to scrape Wellfound via Playwright: {e}")
            
        return jobs

if __name__ == "__main__":
    adapter = WellfoundAdapter()
    jobs = asyncio.run(adapter.fetch_jobs())
    print(f"{adapter.source}: {len(jobs)} jobs")
    if jobs:
        j = jobs[0]
        print(f"  Title: {j['title']}")
        print(f"  Company: {j['company']}")
        print(f"  Location: {j['location']}")
        print(f"  URL: {j['apply_url']}")
        print(f"  Desc preview: {j['description'][:150]}")
