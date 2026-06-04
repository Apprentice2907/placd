"""
Placd — Naukri.com Scraper (v4 — Async Production)

Fast Discovery Phase:
  - curl_cffi with Chrome 124 TLS impersonation
  - Session warming: load Naukri homepage first to get real cookies
  - Fetch pages asynchronously with semaphore
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Optional

from rich.console import Console

from utils.config import (
    MAX_PAGES,
    MAX_RETRIES,
    NAUKRI_RESULTS_PER_PAGE,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    USER_AGENT,
    NAUKRI_CONCURRENCY
)
from scrapers.shared.utils import parse_relative_date, extract_salary_from_text, detect_remote, clean_description

NAUKRI_KEYWORDS = [
    "software developer", "software engineer", "web developer",
    "python developer", "java developer", "react developer",
    "node js developer", "angular developer", "vue js developer",
    "android developer", "ios developer", "flutter developer",
    "data scientist", "machine learning", "deep learning",
    "data analyst", "business analyst", "data engineer",
    "devops", "aws", "azure", "gcp", "kubernetes", "docker",
    "full stack", "backend developer", "frontend developer",
    "php developer", "ruby on rails", ".net developer",
    "salesforce", "sap", "oracle", "cybersecurity",
    "blockchain", "game developer", "embedded systems",
    "qa engineer", "test automation", "performance testing",
    "product manager", "scrum master", "agile coach",
    "ui designer", "ux designer", "graphic designer",
    "technical writer", "solution architect", "system architect",
]

log = logging.getLogger(__name__)
console = Console()

_HOME_URL = "https://www.naukri.com"
_API_URL  = "https://www.naukri.com/jobapi/v1/search"

_API_HEADERS: dict[str, str] = {
    "appid":           "4",
    "systemid":        "110",
    "clientid":        "d3skt0p",
    "User-Agent":      USER_AGENT,
    "Accept":          "application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.naukri.com/",
}

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_naukri(
    query: str = "",
    location: str = "",
    max_pages: int = 50,
    fresher_mode: bool = False,
) -> tuple[list[dict], dict]:
    """
    Scrape Naukri job listings via the v1 JSON API async.
    """
    stats: dict = {
        "source":          "naukri",
        "pages_fetched":   0,
        "fetched":         0,
        "skipped_empty":   0,
        "skipped_error":   0,
        "api_blocked":     False,
        "tier_used":       "curl_cffi/chrome124_async",
        "total_available": 0,
    }

    log.info("Naukri scrape async: location=%r pages=%d", location, max_pages)

    try:
        import curl_cffi.requests as cfr
        session = cfr.AsyncSession(impersonate="chrome124", headers=_API_HEADERS, timeout=REQUEST_TIMEOUT)
    except ImportError:
        console.print("[red]   curl_cffi not available. Cannot scrape Naukri.[/red]")
        stats["api_blocked"] = True
        return [], stats

    all_jobs = []
    try:
        console.print("[dim]   Warming Naukri session...[/dim]")
        warm_ok = await _warm_session(session)
        if not warm_ok:
            console.print("[yellow]   Session warm failed — trying without cookies.[/yellow]")

        queries = [query] if query else NAUKRI_KEYWORDS
        
        for q in queries:
            effective_query = f"{q} fresher" if fresher_mode else q
            jobs = await _scrape_pages(session, effective_query, location or "india",
                                       max_pages, fresher_mode, stats)
            all_jobs.extend(jobs)
    finally:
        await session.close()

    log.info("Naukri scrape complete: fetched=%d skipped_empty=%d skipped_error=%d pages=%d",
             stats["fetched"], stats["skipped_empty"], stats["skipped_error"], stats["pages_fetched"])
    return all_jobs, stats


async def _scrape_pages(
    session,
    query: str,
    location: str,
    max_pages: int,
    fresher_mode: bool,
    stats: dict,
) -> list[dict]:
    
    semaphore = asyncio.Semaphore(NAUKRI_CONCURRENCY)
    jobs = []

    # Naukri API may complain if we fetch page N before page 1, but generally it's fine.
    # To be safe and populate 'totaljobs' from page 1, we could fetch page 1 first, 
    # but for pure async speed, we fire all at once.
    
    tasks = [
        _fetch_page(session, query, location, page_no, semaphore)
        for page_no in range(1, max_pages + 1)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        page_no = i + 1
        if isinstance(result, Exception):
            log.warning(f"Page {page_no} error: {result}")
            continue
            
        raw_jobs, total, ok = result
        if not ok:
            if page_no == 1:
                stats["api_blocked"] = True
            continue

        if page_no == 1:
            stats["total_available"] = total

        for raw in raw_jobs:
            try:
                job = _parse_job(raw, fresher_mode)
                if job:
                    job["source_priority"] = 2  # Higher priority since it's fully enriched from the API
                    jobs.append(job)
                    stats["fetched"] += 1
                else:
                    stats["skipped_empty"] += 1
            except Exception as exc:
                log.warning("Job parse error: %s", exc)
                stats["skipped_error"] += 1
                
        stats["pages_fetched"] += 1

    return jobs


async def _fetch_page(
    session,
    query: str,
    location: str,
    page_no: int,
    semaphore: asyncio.Semaphore,
) -> tuple[list[dict], int, bool]:
    params = {
        "keyword":     query,
        "location":    location,
        "pageNo":      page_no,
        "noOfResults": NAUKRI_RESULTS_PER_PAGE,
        "searchType":  "adv",
    }
    
    async with semaphore:
        console.print(f"[dim]     Naukri page {page_no}...[/dim]")
        resp = await _get_with_retry(session, _API_URL, params=params)
        
        if resp is None:
            return [], 0, False

        try:
            data = resp.json()
        except Exception as exc:
            log.warning("JSON parse error: %s | body[:200]=%r", exc, resp.text[:200])
            return [], 0, False

        raw_jobs: list[dict] = data.get("list", [])
        total: int           = int(data.get("totaljobs", 0))
        
        # Max 10 req/min -> 8-12 seconds jitter
        await asyncio.sleep(random.uniform(8.0, 12.0))
        
        return raw_jobs, total, True


def _parse_job(raw: dict, fresher_mode: bool = True) -> Optional[dict]:
    title   = (raw.get("post") or raw.get("jobSpec") or "").strip()
    company = (raw.get("companyName") or "").strip()
    if not title or not company:
        return None

    url = (raw.get("urlStr") or "").split("?")[0].rstrip("/")
    if not url:
        job_id = str(raw.get("jobId", ""))
        if job_id:
            url = f"https://www.naukri.com/job-listings-{job_id}"
        else:
            return None

    location = _normalise_location(raw)

    min_exp = raw.get("minExp")
    max_exp = raw.get("maxExp")
    min_e, max_e = 0, 0
    if min_exp is not None and max_exp is not None:
        try:
            min_e = int(min_exp)
            max_e = int(max_exp)
            if min_e == 0 and max_e == 0:
                experience = "Fresher"
            elif min_e == 0:
                experience = f"0-{max_e} Yrs"
            else:
                experience = f"{min_e}-{max_e} Yrs"
        except (ValueError, TypeError):
            experience = ""
    else:
        experience = ""

    if fresher_mode and min_exp is not None:
        try:
            if int(min_exp) > 2:
                return None
        except (ValueError, TypeError):
            pass

    salary = _normalise_salary(raw)
    sal_min, sal_max, sal_curr = extract_salary_from_text(salary)

    raw_desc = raw.get("jobDesc") or raw.get("tupleDesc") or ""
    description = clean_description(raw_desc).strip()
    if not sal_min and not sal_max:
        sal_min, sal_max, sal_curr = extract_salary_from_text(description)

    keywords_raw = raw.get("keywords") or ""
    seen: set[str] = set()
    unique_skills: list[str] = []
    
    # Also grab skills from keySkills array if present
    key_skills = raw.get("keySkills") or []
    if isinstance(key_skills, list):
        for sk in key_skills:
            if isinstance(sk, dict) and "label" in sk:
                unique_skills.append(sk["label"])
                seen.add(sk["label"].lower())

    for s in (s.strip() for s in keywords_raw.split(",") if s.strip()):
        low = s.lower()
        if low not in seen:
            seen.add(low)
            unique_skills.append(s)
    skills = ", ".join(unique_skills)

    posted_date_raw = str(raw.get("addDate") or raw.get("dateAdded") or "").strip()
    posted_date = parse_relative_date(posted_date_raw).isoformat()

    emp_type   = raw.get("employmentType") or ""
    job_code   = raw.get("jobtype") or ""
    if job_code == "i":
        job_type = f"Internship"
    elif experience:
        job_type = f"Entry"
    else:
        job_type = emp_type or "Full Time"

    is_wfh = raw.get("workFromHome", False)
    is_remote = is_wfh or detect_remote(title, location, description)

    return {
        "title":         title,
        "company":       company,
        "location":      location,
        "job_type":      job_type,
        "salary":        salary,
        "salary_min":    sal_min,
        "salary_max":    sal_max,
        "salary_currency": sal_curr,
        "description":   description,
        "skills":        skills,
        "url":           url,
        "source":        "naukri",
        "apply_url":     url,
        "hiring_status": "",
        "duration":      str(raw.get("internshipDuration") or ""),
        "experience":    experience,
        "experience_min": min_e,
        "experience_max": max_e,
        "posted_date":   posted_date,
        "company_rating": str(raw.get("ambitionBoxData", {}).get("aggregateRating", "")),
        "applicants":    int(raw.get("jobApplications", 0)) if raw.get("jobApplications") else 0,
        "is_remote":     is_remote,
        "tags":          raw.get("jobTags", [])
    }


def _normalise_location(raw: dict) -> str:
    cityfield = (raw.get("cityfield") or "").strip()
    if cityfield:
        city = _extract_city_from_cityfield(cityfield)
        if city:
            return city
    for key in ("city", "CONTCITY"):
        val = (raw.get(key) or "").strip()
        val = re.sub(r"^(hybrid|remote)\s*[-—]\s*", "", val, flags=re.IGNORECASE).strip()
        if val:
            return val
    return ""


_LOC_EXCLUDE: frozenset[str] = frozenset({
    "Metropolitan", "Cities", "North", "South", "East", "West",
    "Top", "Anywhere", "India", "Popular", "Locations", "Preferred",
    "Jobseeker", "National", "Capital", "Region", "NCR", "Territory",
})


def _extract_city_from_cityfield(text: str) -> str:
    for word in reversed(text.split()):
        if len(word) >= 3 and word[0].isupper() and "/" not in word and word not in _LOC_EXCLUDE:
            return word
    if " - " in text:
        return text.split(" - ")[0].strip().title()
    return text.split()[0].title() if text.strip() else ""


def _normalise_salary(raw: dict) -> str:
    salary_str = (raw.get("SALARY") or "").strip()
    if salary_str and salary_str not in ("0", "Not Disclosed"):
        return salary_str
    try:
        min_s = int(raw.get("minSal", 0))
        max_s = int(raw.get("maxSal", 0))
    except (ValueError, TypeError):
        return ""
    if min_s == 0 and max_s == 0:
        return "Not Disclosed"
    if min_s == max_s:
        return f"{min_s} LPA"
    return f"{min_s}-{max_s} LPA"


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _warm_session(session) -> bool:
    try:
        resp = await session.get(_HOME_URL)
        return resp.status_code == 200
    except Exception as exc:
        log.warning("Session warm failed: %s", exc)
        return False


async def _get_with_retry(
    session,
    url: str,
    params: Optional[dict] = None,
    max_retries: int = MAX_RETRIES,
):
    for attempt in range(max_retries + 1):
        try:
            resp = await session.get(url, params=params)

            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1.0, 3.0)
                await asyncio.sleep(wait)
                continue

            if resp.status_code in (403, 406, 401):
                log.warning(f"Session expired with {resp.status_code}, refreshing...")
                await _warm_session(session)
                if attempt < max_retries:
                    continue
                return None 

            if resp.status_code >= 500:
                wait = RETRY_BACKOFF ** attempt
                if attempt < max_retries:
                    await asyncio.sleep(wait)
                    continue
                return None

            resp.raise_for_status()
            return resp

        except Exception as exc:
            wait = RETRY_BACKOFF ** attempt
            if attempt < max_retries:
                await asyncio.sleep(wait)
            else:
                return None

    return None

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    
    async def main():
        jobs, stats = await scrape_naukri("python developer", max_pages=1)
        print(stats)
        for r in jobs[:3]:
            print(f"  {r['title']} @ {r['company']} — {r['location']}")
        print(f"\nTotal: {len(jobs)} jobs")
        
    asyncio.run(main())
