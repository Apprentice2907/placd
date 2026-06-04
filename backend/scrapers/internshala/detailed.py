"""
Placd — Internshala Detailed Scraper

Deep scrape of internshala.com/internships that extracts ALL fields:
  - title, company, company_logo_url, location, stipend (exact text),
    duration, skills, who_can_apply (eligibility), last_date, apply_url

Uses requests + BeautifulSoup. Parses div.internship_meta and span.stipend.
Stores company_logo_url, who_can_apply, and stipend_display in the PostgreSQL schema.
"""

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from utils.config import (
    USER_AGENT, REQUEST_TIMEOUT, REQUEST_DELAY,
    MAX_PAGES, MAX_RETRIES, RETRY_BACKOFF,
    INTERNSHALA_CONCURRENCY,
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

# Eligibility keywords we care about
ELIGIBLE_KEYWORDS = ["3rd year", "third year", "pre-final", "all years", "any year"]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_internshala_detailed(
    query: str = "",
    location: str = "",
    max_pages: int = MAX_PAGES,
) -> list[dict]:
    """
    Deep scrape of Internshala that fetches listing pages, then enriches
    each internship with its detail page to extract logo, eligibility,
    stipend text, skills, duration, and last_date.
    """
    search_url = _build_search_url(query, location)
    semaphore = asyncio.Semaphore(INTERNSHALA_CONCURRENCY)

    async with httpx.AsyncClient(
        headers=_DEFAULT_HEADERS,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        # Phase 1: Discover listing URLs from search pages
        console.print(f"[bold cyan]Internshala Detailed[/] — Discovering listings (max {max_pages} pages)...")
        
        discovery_tasks = [
            _fetch_listing_page(client, search_url, page, semaphore)
            for page in range(1, max_pages + 1)
        ]
        page_results = await asyncio.gather(*discovery_tasks, return_exceptions=True)

        # Collect unique listing URLs with preview data
        listings: list[dict] = []
        seen_urls: set[str] = set()
        for result in page_results:
            if isinstance(result, Exception):
                log.warning("Internshala listing page error: %s", result)
                continue
            for item in result:
                url = item.get("apply_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    listings.append(item)

        console.print(f"[bold cyan]Internshala Detailed[/] — Found {len(listings)} unique listings. Enriching...")

        # Phase 2: Fetch detail pages to extract deep fields
        enrich_tasks = [
            _enrich_from_detail_page(client, listing, semaphore)
            for listing in listings
        ]
        enriched_results = await asyncio.gather(*enrich_tasks, return_exceptions=True)

    jobs: list[dict] = []
    for result in enriched_results:
        if isinstance(result, Exception):
            log.warning("Internshala detail enrichment error: %s", result)
            continue
        if result:
            jobs.append(result)

    console.print(f"[bold green]Internshala Detailed[/] — {len(jobs)} jobs fully scraped.")
    return jobs


def eligibility_match(who_can_apply: str) -> bool:
    """
    Check if the who_can_apply text indicates eligibility for
    3rd year / pre-final / all years students.
    """
    if not who_can_apply:
        return False
    text_lower = who_can_apply.lower()
    return any(kw in text_lower for kw in ELIGIBLE_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# Internal — Listing page parsing
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_listing_page(
    client: httpx.AsyncClient,
    search_url: str,
    page: int,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Fetch one search-results page and extract preview cards."""
    page_url = f"{search_url}/page-{page}" if page > 1 else search_url

    async with semaphore:
        console.print(f"[dim]     Listing page {page}...[/dim]")
        resp = await _get_with_retry(client, page_url)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".individual_internship, .internship_meta")

        items: list[dict] = []
        for card in cards:
            item = _parse_listing_card(card)
            if item and item.get("apply_url"):
                items.append(item)

        return items


def _parse_listing_card(card: BeautifulSoup) -> Optional[dict]:
    """
    Extract preview-level data from a search result card.
    Returns a dict with keys matching the unified schema.
    """
    # ── Title ──
    title = _text(card, ".profile a, h3.heading_4_5 a, .job-internship-name a, a.job-title-href")

    # ── Company ──
    company = _text(card, ".company_name a, h4.heading_6 a, .company-name, p.company-name")

    # ── Company logo ──
    logo_el = card.select_one(".internship_logo img, .company_logo img, img.logo")
    company_logo_url = ""
    if logo_el:
        company_logo_url = logo_el.get("src", "") or logo_el.get("data-src", "")
        if company_logo_url and not company_logo_url.startswith("http"):
            company_logo_url = f"{BASE_URL}{company_logo_url}"

    # ── Location ──
    location = _text(card, ".locations a, #location_names a, .location_link, a.location_link")

    # ── Stipend (preview) ──
    stipend = _text(card, "span.stipend, .desktop-text .stipend, .stipend")

    # ── Detail URL ──
    detail_url = ""
    for selector in (
        "a.view_detail_button",
        ".profile a[href*='/internship/']",
        "h3.heading_4_5 a",
        ".job-internship-name a",
        "a.job-title-href",
    ):
        el = card.select_one(selector)
        if el and el.get("href"):
            href = el["href"]
            detail_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            break

    if not detail_url:
        return None

    return {
        "title": title,
        "company": company,
        "company_logo_url": company_logo_url,
        "location": location,
        "stipend_display": stipend,
        "salary": stipend,
        "apply_url": detail_url,
        "url": detail_url,
        "source": "internshala",
        "source_priority": 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal — Detail page enrichment
# ─────────────────────────────────────────────────────────────────────────────

async def _enrich_from_detail_page(
    client: httpx.AsyncClient,
    listing: dict,
    semaphore: asyncio.Semaphore,
) -> Optional[dict]:
    """
    Fetch the detail page for a single internship listing and extract
    deep fields: skills, who_can_apply, duration, last_date, full stipend,
    and a better logo URL.
    """
    url = listing.get("apply_url", "")
    if not url:
        return listing

    async with semaphore:
        # Small respectful delay
        await asyncio.sleep(random.uniform(0.3, 1.0))
        resp = await _get_with_retry(client, url)
        if not resp:
            return listing

    soup = BeautifulSoup(resp.text, "html.parser")
    enriched = dict(listing)  # shallow copy

    # ── Better logo from detail page ──
    if not enriched.get("company_logo_url"):
        logo_el = soup.select_one(".internship_logo img, .company_logo img, img.logo, .detail-company-logo img")
        if logo_el:
            src = logo_el.get("src", "") or logo_el.get("data-src", "")
            if src:
                enriched["company_logo_url"] = src if src.startswith("http") else f"{BASE_URL}{src}"

    # ── Stipend (detail — often more precise) ──
    stipend_el = soup.select_one("span.stipend, .stipend_container .stipend, #stipend_container_desktop span.stipend")
    if stipend_el:
        stipend_text = stipend_el.get_text(strip=True)
        if stipend_text:
            enriched["stipend_display"] = stipend_text
            enriched["salary"] = stipend_text

    # ── Duration ──
    duration_text = _extract_detail_field(soup, "Duration")
    if duration_text:
        enriched["duration"] = duration_text

    # ── Skills / Key Skills ──
    skills_section = soup.select(".round_tabs .round_tabs_item, .skills_container .skill_tag, span.round_tabs")
    if skills_section:
        skills_list = [el.get_text(strip=True) for el in skills_section if el.get_text(strip=True)]
        enriched["skills"] = ", ".join(skills_list)
    else:
        # Fallback: look for "Skill(s) required" section
        skill_text = _extract_detail_field(soup, "Skill(s) required")
        if skill_text:
            enriched["skills"] = skill_text

    # ── Who can apply / Eligibility ──
    who_can_section = soup.select_one("#who_can_apply, .who_can_apply, div[id*='who_can_apply']")
    if who_can_section:
        who_text = who_can_section.get_text(separator=" ", strip=True)
        # Clean up "Who can apply" header if present
        who_text = re.sub(r"^Who\s+can\s+apply\s*", "", who_text, flags=re.IGNORECASE).strip()
        enriched["who_can_apply"] = who_text
    else:
        # Fallback: search for eligibility-related text in description
        eligibility_text = _extract_detail_field(soup, "Who can apply")
        if eligibility_text:
            enriched["who_can_apply"] = eligibility_text
        else:
            enriched["who_can_apply"] = ""

    # ── Last Date / Apply By ──
    last_date = _extract_detail_field(soup, "Apply By")
    if not last_date:
        last_date = _extract_detail_field(soup, "Last Date")
    if not last_date:
        # Try the specific element
        deadline_el = soup.select_one(".apply_by .item_body, #apply-by-date")
        if deadline_el:
            last_date = deadline_el.get_text(strip=True)
    enriched["last_date"] = last_date or ""

    # ── Description (full) ──
    desc_el = soup.select_one(".internship_details .text-container, .about_company_text_container, #about_internship")
    if desc_el:
        enriched["description"] = desc_el.get_text(separator="\n", strip=True)
    else:
        enriched["description"] = enriched.get("description", "")

    # ── Job type classification ──
    enriched["job_type"] = "internship"
    enriched["is_internship"] = True
    enriched["scraped_at"] = datetime.now().isoformat()

    return enriched


def _extract_detail_field(soup: BeautifulSoup, label: str) -> str:
    """
    Find a detail field by its label text in the detail page.
    Internshala uses patterns like:
      <div class="item_heading">Duration</div>
      <div class="item_body">3 Months</div>
    """
    # Strategy 1: .item_heading + .item_body pairs
    headings = soup.select(".item_heading, .detail_heading, dt, .ic-heading")
    for h in headings:
        if label.lower() in h.get_text(strip=True).lower():
            sibling = h.find_next_sibling()
            if sibling:
                return sibling.get_text(strip=True)
            parent = h.parent
            if parent:
                body = parent.select_one(".item_body, .detail_body, dd, .ic-body")
                if body:
                    return body.get_text(strip=True)

    # Strategy 2: text-based search in divs
    for div in soup.find_all(["div", "span", "p"], string=re.compile(re.escape(label), re.IGNORECASE)):
        sibling = div.find_next_sibling()
        if sibling:
            return sibling.get_text(strip=True)

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Internal — Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _build_search_url(query: str, location: str) -> str:
    if query:
        query_slug = query.lower().strip().replace(" ", "-")
        url = f"{BASE_URL}/internships/{query_slug}-internship"
    else:
        url = f"{BASE_URL}/internships"
    if location and location.lower() not in ("india", ""):
        loc_slug = location.lower().strip().replace(" ", "-")
        url += f"/in-{loc_slug}"
    return url


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = MAX_RETRIES,
) -> Optional[httpx.Response]:
    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url)

            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1.0, 3.0)
                log.warning("Rate limited on %s, waiting %.1fs", url, wait)
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
                log.warning("Request error (%s): %s", url, exc)
                return None

    return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI Test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    async def main():
        jobs = await scrape_internshala_detailed("python developer", max_pages=1)
        for r in jobs[:3]:
            eligible = eligibility_match(r.get("who_can_apply", ""))
            print(f"  {r['title']} @ {r['company']}")
            print(f"    Logo:       {r.get('company_logo_url', 'N/A')}")
            print(f"    Stipend:    {r.get('stipend_display', 'N/A')}")
            print(f"    Duration:   {r.get('duration', 'N/A')}")
            print(f"    Skills:     {r.get('skills', 'N/A')}")
            print(f"    Eligible:   {eligible} — {r.get('who_can_apply', '')[:80]}")
            print(f"    Last Date:  {r.get('last_date', 'N/A')}")
            print()
        print(f"\nTotal: {len(jobs)} jobs")

    asyncio.run(main())
