"""
Placd — Internshala Scraper (v3 - Async Discovery)

Fast Discovery Phase:
  - Paginate search results concurrently using httpx.AsyncClient
  - Collect listing URLs and preview data (title, company, location, salary)
  - Yield "raw" lightweight jobs immediately
  - Enrichment (descriptions, skills) happens later in the background queue
"""

import asyncio
import random
import logging
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from utils.config import (
    USER_AGENT, REQUEST_TIMEOUT, REQUEST_DELAY,
    MAX_PAGES, MAX_RETRIES, RETRY_BACKOFF,
    INTERNSHALA_CONCURRENCY
)

console = Console()
log = logging.getLogger(__name__)

BASE_URL = "https://internshala.com"

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_internshala(
    query: str,
    location: str = "",
    max_pages: int = MAX_PAGES,
) -> list[dict]:
    """
    Fast discovery phase for Internshala.
    Fetches search pages asynchronously, extracts preview cards, and yields raw jobs.
    """
    search_url = _build_search_url(query, location)
    semaphore = asyncio.Semaphore(INTERNSHALA_CONCURRENCY)

    async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT) as client:
        # We need to fetch page 1 to know if there are more pages, but for speed,
        # we can blindly fetch pages 1..max_pages concurrently. If a page is empty,
        # we'll just ignore it. Internshala handles out-of-bounds pagination gracefully.
        
        tasks = [
            _fetch_search_page(client, search_url, page, max_pages, semaphore)
            for page in range(1, max_pages + 1)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs: list[dict] = []
    seen: set[str] = set()

    for result in results:
        if isinstance(result, Exception):
            log.warning("Internshala page fetch error: %s", result)
            continue
        
        for job in result:
            if job["url"] not in seen:
                seen.add(job["url"])
                jobs.append(job)

    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Internal
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_search_page(
    client: httpx.AsyncClient,
    search_url: str,
    page: int,
    max_pages: int,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Fetch a single search results page and extract preview jobs."""
    page_url = f"{search_url}/page-{page}" if page > 1 else search_url
    
    async with semaphore:
        console.print(f"[dim]     Search page {page}/{max_pages}...[/dim]")
        resp = await _get_with_retry(client, page_url)
        
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".individual_internship")
        
        jobs = []
        for card in cards:
            url, preview = _extract_url_and_preview(card)
            if url:
                jobs.append({
                    "url": url,
                    "title": preview.get("title", ""),
                    "company": preview.get("company", ""),
                    "location": preview.get("location", ""),
                    "salary": preview.get("salary", ""),
                    "source": "internshala",
                    "description": "",  # To be enriched later
                    "skills": "",       # To be enriched later
                    "source_priority": 1, # Normal priority
                })
        
        return jobs


def _extract_url_and_preview(card: BeautifulSoup) -> tuple[str, dict]:
    """Extract the detail-page URL and preview fields from a search result card."""
    url = ""
    for selector in (
        "a.view_detail_button",
        ".profile a[href*='/internship/']",
        "h3.heading_4_5 a",
        ".job-internship-name a",
    ):
        el = card.select_one(selector)
        if el and el.get("href"):
            href = el["href"]
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            break

    preview = {
        "title":    _text(card, ".profile a, h3.heading_4_5 a, .job-internship-name a"),
        "company":  _text(card, ".company_name a, h4.heading_6 a, .company-name"),
        "location": _text(card, ".locations a, #location_names a, .location_link"),
        "salary":   _text(card, ".stipend, .desktop-text .stipend"),
    }
    return url, preview


def _text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _build_search_url(query: str, location: str) -> str:
    query_slug = query.lower().strip().replace(" ", "-")
    url = f"{BASE_URL}/internships/{query_slug}-internship"
    if location and location.lower() not in ("india", ""):
        loc_slug = location.lower().strip().replace(" ", "-")
        url += f"/in-{loc_slug}"
    return url


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = MAX_RETRIES,
) -> httpx.Response | None:
    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url)

            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1.0, 3.0)
                await asyncio.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = RETRY_BACKOFF ** attempt
                if attempt < max_retries:
                    await asyncio.sleep(wait)
                    continue
                return None

            resp.raise_for_status()
            return resp

        except httpx.RequestError as exc:
            wait = RETRY_BACKOFF ** attempt
            if attempt < max_retries:
                await asyncio.sleep(wait)
            else:
                log.warning(f"Request error ({url}): {exc}")
                return None

    return None

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    
    async def main():
        jobs = await scrape_internshala("python developer", max_pages=1)
        for r in jobs[:3]:
            print(f"  {r['title']} @ {r['company']} — {r['location']}")
        print(f"\nTotal: {len(jobs)} jobs")
        
    asyncio.run(main())
