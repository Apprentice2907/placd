"""
Placd — LinkedIn Jobs Scraper via Apify REST API

Uses the Apify LinkedIn Jobs Scraper actor (hKByXkMQaC5Qt9UMH)
to fetch structured job data without Playwright or browser overhead.

Only runs for roles specified in PRIORITY_ROLES to avoid wasting API credits.
Requires APIFY_API_TOKEN in environment or .env.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import httpx
from rich.console import Console

from utils.config import USER_AGENT, REQUEST_TIMEOUT

console = Console()
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
ACTOR_ID = "hKByXkMQaC5Qt9UMH"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"

# Only scrape LinkedIn for these high-value roles
PRIORITY_ROLES = [
    "Software Engineer Intern",
    "Software Developer Intern",
    "Data Science Intern",
    "Machine Learning Intern",
    "Backend Developer Intern",
    "Frontend Developer Intern",
    "Full Stack Developer Intern",
    "Product Manager Intern",
    "DevOps Intern",
    "Cloud Engineer Intern",
    "AI Research Intern",
    "Quantitative Analyst Intern",
    "Software Engineer New Grad",
    "Data Analyst",
    "Python Developer",
    "React Developer",
    "Site Reliability Engineer",
]

MAX_RESULTS_PER_ROLE = 50
APIFY_TIMEOUT = 120  # seconds — Apify sync runs can take a while


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_linkedin_apify(
    role: str,
    location: str = "United States",
    max_results: int = MAX_RESULTS_PER_ROLE,
) -> list[dict]:
    """
    Call the Apify LinkedIn Jobs Scraper for a single role+location.
    Returns a list of dicts in the unified Placd schema.

    Only processes roles that appear in PRIORITY_ROLES (case-insensitive match).
    """
    # Gate: only scrape priority roles
    if not _is_priority_role(role):
        console.print(f"[yellow]LinkedIn Apify[/] — Skipping non-priority role: {role}")
        return []

    if not APIFY_API_TOKEN:
        console.print("[red]LinkedIn Apify[/] — APIFY_API_TOKEN not set. Skipping.")
        log.error("APIFY_API_TOKEN is not configured. Cannot scrape LinkedIn via Apify.")
        return []

    console.print(f"[bold magenta]LinkedIn Apify[/] — Scraping '{role}' in '{location}' (max {max_results})...")

    payload = {
        "searchUrl": _build_linkedin_search_url(role, location),
        "maxItems": max_results,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIFY_API_TOKEN}",
        "User-Agent": USER_AGENT,
    }

    try:
        async with httpx.AsyncClient(timeout=APIFY_TIMEOUT) as client:
            resp = await client.post(
                APIFY_RUN_URL,
                json=payload,
                headers=headers,
                params={"token": APIFY_API_TOKEN},
            )

            if resp.status_code == 402:
                console.print("[red]LinkedIn Apify[/] — Apify quota exceeded (402). Skipping.")
                log.warning("Apify quota exceeded for role=%s", role)
                return []

            if resp.status_code != 200:
                console.print(f"[red]LinkedIn Apify[/] — HTTP {resp.status_code}: {resp.text[:200]}")
                log.warning("Apify returned %d for role=%s", resp.status_code, role)
                return []

            raw_items = resp.json()

    except httpx.TimeoutException:
        console.print(f"[yellow]LinkedIn Apify[/] — Timeout after {APIFY_TIMEOUT}s for '{role}'.")
        log.warning("Apify timeout for role=%s", role)
        return []
    except Exception as e:
        console.print(f"[red]LinkedIn Apify[/] — Error: {e}")
        log.error("Apify error for role=%s: %s", role, e)
        return []

    # Map Apify response to our unified schema
    jobs = []
    for item in raw_items:
        job = _map_apify_to_schema(item, role)
        if job:
            jobs.append(job)

    console.print(f"[bold green]LinkedIn Apify[/] — Got {len(jobs)} jobs for '{role}'.")
    return jobs


async def scrape_all_priority_roles(
    location: str = "United States",
    max_results_per_role: int = MAX_RESULTS_PER_ROLE,
    concurrency: int = 2,
) -> list[dict]:
    """
    Run the Apify scraper for all PRIORITY_ROLES sequentially
    (limited concurrency to respect Apify rate limits).
    """
    semaphore = asyncio.Semaphore(concurrency)
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    async def _scrape_one(role: str):
        async with semaphore:
            return await scrape_linkedin_apify(role, location, max_results_per_role)

    tasks = [_scrape_one(role) for role in PRIORITY_ROLES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            log.warning("Priority role scrape error: %s", result)
            continue
        for job in result:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(job)

    console.print(f"[bold green]LinkedIn Apify[/] — Total: {len(all_jobs)} unique jobs across {len(PRIORITY_ROLES)} roles.")
    return all_jobs


# ─────────────────────────────────────────────────────────────────────────────
# Internal
# ─────────────────────────────────────────────────────────────────────────────

def _is_priority_role(role: str) -> bool:
    """Check if the given role is in the PRIORITY_ROLES list (case-insensitive)."""
    role_lower = role.lower().strip()
    return any(pr.lower().strip() == role_lower for pr in PRIORITY_ROLES)


def _build_linkedin_search_url(role: str, location: str) -> str:
    """Build a LinkedIn guest job search URL."""
    import urllib.parse
    params = urllib.parse.urlencode({"keywords": role, "location": location})
    return f"https://www.linkedin.com/jobs/search/?{params}"


def _map_apify_to_schema(item: dict, search_role: str) -> Optional[dict]:
    """
    Map an Apify LinkedIn Jobs Scraper result to our unified job schema.

    Apify actor hKByXkMQaC5Qt9UMH returns fields like:
      title, companyName, companyUrl, location, postedAt, salary,
      applicationsCount, description, link, contractType, experienceLevel,
      companyLogo, seniorityLevel, jobFunction, industries
    """
    title = (item.get("title") or "").strip()
    company = (item.get("companyName") or "").strip()
    url = (item.get("link") or item.get("url") or "").strip()

    if not title or not url:
        return None

    # Clean tracking params from URL
    url = url.split("?")[0]

    # Extract salary display
    salary = (item.get("salary") or "").strip()

    # Determine job type from contractType and search context
    contract_type = (item.get("contractType") or "").lower()
    seniority = (item.get("seniorityLevel") or item.get("experienceLevel") or "").lower()

    if "intern" in contract_type or "intern" in title.lower() or "intern" in search_role.lower():
        job_type = "internship"
        is_internship = True
    elif "entry" in seniority or "new grad" in search_role.lower():
        job_type = "full-time"
        is_internship = False
    else:
        job_type = contract_type or "full-time"
        is_internship = False

    # Location and remote detection
    location = (item.get("location") or "").strip()
    is_remote = "remote" in location.lower() or "remote" in (item.get("workType") or "").lower()

    return {
        "title": title,
        "company": company,
        "company_logo_url": (item.get("companyLogo") or item.get("companyLogoUrl") or "").strip(),
        "location": location,
        "job_type": job_type,
        "salary": salary,
        "stipend_display": salary if is_internship else "",
        "description": (item.get("description") or "").strip(),
        "url": url,
        "apply_url": url,
        "source": "linkedin_apify",
        "source_priority": 8,
        "skills": "",
        "duration": "",
        "experience": seniority,
        "posted_date": (item.get("postedAt") or item.get("publishedAt") or "").strip(),
        "is_remote": is_remote,
        "is_internship": is_internship,
        "who_can_apply": "",
        "scraped_at": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    async def main():
        # Test with a single priority role
        jobs = await scrape_linkedin_apify("Software Engineer Intern", "United States", max_results=5)
        for r in jobs[:3]:
            print(f"  {r['title']} @ {r['company']}")
            print(f"    Logo:     {r.get('company_logo_url', 'N/A')}")
            print(f"    Location: {r['location']}")
            print(f"    Salary:   {r.get('salary', 'N/A')}")
            print(f"    URL:      {r['url']}")
            print()
        print(f"\nTotal: {len(jobs)} jobs")

    asyncio.run(main())
