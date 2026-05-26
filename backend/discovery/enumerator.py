import asyncio
import re
import random
import logging
from typing import List, Dict, Any, Set
from urllib.parse import urlparse, unquote
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from celery import shared_task
from sqlalchemy import text
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Local imports
from db.connection import AsyncSessionLocal
from discovery.seed_lists import (
    ALL_SEED_LISTS,
    FAANG_COMPANIES,
    TOP_STARTUPS,
    HFT_FIRMS,
    AI_LABS
)

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Quick lookup for priority
KNOWN_SLUGS = {}
for lst, priority in [(FAANG_COMPANIES, 1), (HFT_FIRMS, 1), (AI_LABS, 1), (TOP_STARTUPS, 2)]:
    for comp in lst:
        KNOWN_SLUGS[comp["ats_slug"]] = priority


def get_priority_for_slug(slug: str) -> int:
    return KNOWN_SLUGS.get(slug, 5)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
)
async def _fetch_commoncrawl(url: str) -> List[Dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        results = []
        for line in response.text.strip().split("\n"):
            if line:
                try:
                    import json
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return results


async def enumerate_greenhouse_slugs() -> List[Dict]:
    """Strategy: Query CommonCrawl CDX API for boards.greenhouse.io/*/jobs"""
    log.info("Starting Greenhouse enumeration...")
    url = "https://index.commoncrawl.org/CC-MAIN-2024-10-index?url=boards.greenhouse.io%2F*%2Fjobs&output=json&limit=50000"
    
    companies = []
    seen = set()
    
    try:
        data = await _fetch_commoncrawl(url)
        for row in data:
            row_url = row.get("url", "")
            match = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs', row_url)
            if match:
                slug = match.group(1).lower()
                if slug not in seen:
                    seen.add(slug)
                    companies.append({
                        "name": slug.replace("-", " ").title(),
                        "ats_type": "greenhouse",
                        "ats_slug": slug,
                        "careers_url": f"https://boards.greenhouse.io/v1/boards/{slug}/jobs",
                        "domain": f"{slug}.com"  # fallback domain
                    })
    except Exception as e:
        log.error(f"Error enumerating Greenhouse: {e}")
        
    return companies


async def enumerate_lever_slugs() -> List[Dict]:
    """Strategy: CommonCrawl CDX for jobs.lever.co/*/jobs"""
    log.info("Starting Lever enumeration...")
    url = "https://index.commoncrawl.org/CC-MAIN-2024-10-index?url=jobs.lever.co%2F*&output=json&limit=50000"
    
    companies = []
    seen = set()
    
    try:
        data = await _fetch_commoncrawl(url)
        for row in data:
            row_url = row.get("url", "")
            match = re.search(r'jobs\.lever\.co/([^/]+)', row_url)
            if match:
                slug = match.group(1).lower()
                if slug not in seen and slug != "jobs":
                    seen.add(slug)
                    companies.append({
                        "name": slug.replace("-", " ").title(),
                        "ats_type": "lever",
                        "ats_slug": slug,
                        "careers_url": f"https://jobs.lever.co/{slug}",
                        "domain": f"{slug}.com"
                    })
    except Exception as e:
        log.error(f"Error enumerating Lever: {e}")
        
    return companies


async def enumerate_ashby_slugs() -> List[Dict]:
    """Strategy: CommonCrawl CDX for jobs.ashbyhq.com/*/jobs"""
    log.info("Starting Ashby enumeration...")
    url = "https://index.commoncrawl.org/CC-MAIN-2024-10-index?url=jobs.ashbyhq.com%2F*&output=json&limit=50000"
    
    companies = []
    seen = set()
    
    try:
        data = await _fetch_commoncrawl(url)
        for row in data:
            row_url = row.get("url", "")
            match = re.search(r'jobs\.ashbyhq\.com/([^/]+)', row_url)
            if match:
                slug = match.group(1).lower()
                if slug not in seen:
                    seen.add(slug)
                    companies.append({
                        "name": slug.replace("-", " ").title(),
                        "ats_type": "ashby",
                        "ats_slug": slug,
                        "careers_url": f"https://jobs.ashbyhq.com/{slug}",
                        "domain": f"{slug}.com"
                    })
    except Exception as e:
        log.error(f"Error enumerating Ashby: {e}")
        
    return companies


async def enumerate_workday_domains() -> List[Dict]:
    """Strategy: CommonCrawl CDX for *.wd*.myworkdayjobs.com"""
    log.info("Starting Workday enumeration...")
    companies = []
    seen = set()
    
    wd_patterns = [
        "*.wd1.myworkdayjobs.com%2F*",
        "*.wd3.myworkdayjobs.com%2F*",
        "*.wd5.myworkdayjobs.com%2F*"
    ]
    
    for pattern in wd_patterns:
        url = f"https://index.commoncrawl.org/CC-MAIN-2024-10-index?url={pattern}&output=json&limit=20000"
        try:
            data = await _fetch_commoncrawl(url)
            for row in data:
                row_url = row.get("url", "")
                parsed = urlparse(row_url)
                host = parsed.netloc
                
                # host like: company.wd1.myworkdayjobs.com
                parts = host.split(".")
                if len(parts) >= 4 and parts[-2] == "myworkdayjobs":
                    slug = parts[0].lower()
                    if slug not in seen:
                        seen.add(slug)
                        companies.append({
                            "name": slug.replace("-", " ").title(),
                            "ats_type": "workday",
                            "ats_slug": slug,
                            "careers_url": f"https://{host}",
                            "domain": f"{slug}.com"
                        })
        except Exception as e:
            log.error(f"Error enumerating Workday pattern {pattern}: {e}")
            
    return companies


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=10)
)
async def google_dork_discovery(ats_type: str) -> List[Dict]:
    """
    Query google for ATS domains.
    Supported ats_types: greenhouse, lever, ashby, workday
    """
    log.info(f"Starting Google Dork discovery for {ats_type}...")
    
    site_query = {
        "greenhouse": "site:boards.greenhouse.io",
        "lever": "site:jobs.lever.co",
        "ashby": "site:jobs.ashbyhq.com",
        "workday": "site:myworkdayjobs.com",
    }.get(ats_type)
    
    if not site_query:
        return []

    companies = []
    seen = set()
    
    # Simple pagination
    for page in range(3):
        start = page * 10
        url = f"https://www.google.com/search?q={site_query}&start={start}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = unquote(a['href'])
                    
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                        
                    slug = None
                    if ats_type == "greenhouse":
                        match = re.search(r'boards\.greenhouse\.io/([^/]+)', href)
                        if match: slug = match.group(1).lower()
                    elif ats_type == "lever":
                        match = re.search(r'jobs\.lever\.co/([^/]+)', href)
                        if match: slug = match.group(1).lower()
                    elif ats_type == "ashby":
                        match = re.search(r'jobs\.ashbyhq\.com/([^/]+)', href)
                        if match: slug = match.group(1).lower()
                    elif ats_type == "workday":
                        match = re.search(r'([^/]+)\.wd\d\.myworkdayjobs\.com', href)
                        if match: slug = match.group(1).lower()
                        
                    if slug and slug not in seen and not slug.startswith("www"):
                        seen.add(slug)
                        companies.append({
                            "name": slug.replace("-", " ").title(),
                            "ats_type": ats_type,
                            "ats_slug": slug,
                            "careers_url": href,
                            "domain": f"{slug}.com"
                        })
                        
        except Exception as e:
            log.warning(f"Google dork failed for {ats_type} on page {page}: {e}")
            
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
    return companies


async def save_companies_batch(companies: List[Dict], db=None) -> int:
    """
    Bulk upsert into companies table using ON CONFLICT (domain).
    """
    if not companies:
        return 0
        
    # Deduplicate by domain to avoid postgres errors within a single statement
    unique_companies = {}
    for comp in companies:
        domain = comp.get("domain") or f"{comp['ats_slug']}.com"
        if domain not in unique_companies:
            comp["domain"] = domain
            comp["crawl_priority"] = get_priority_for_slug(comp["ats_slug"])
            unique_companies[domain] = comp
            
    insert_data = list(unique_companies.values())
    
    query = text("""
        INSERT INTO companies (name, domain, ats_type, ats_slug, careers_url, crawl_priority)
        VALUES (:name, :domain, :ats_type, :ats_slug, :careers_url, :crawl_priority)
        ON CONFLICT (domain) DO UPDATE SET
            ats_type = EXCLUDED.ats_type,
            ats_slug = EXCLUDED.ats_slug,
            careers_url = EXCLUDED.careers_url,
            crawl_priority = EXCLUDED.crawl_priority,
            updated_at = NOW()
    """)
    
    count = 0
    # Create our own session if none provided
    session_generator = db if db else AsyncSessionLocal()
    
    try:
        # If db is passed as AsyncSessionLocal, it's an async context manager, otherwise might be a session object directly.
        # Handling both patterns:
        session = session_generator if hasattr(session_generator, 'execute') else None
        context = None
        if not session:
            context = session_generator
            session = await context.__aenter__()

        for idx in range(0, len(insert_data), 500):
            batch = insert_data[idx:idx + 500]
            await session.execute(query, batch)
            count += len(batch)
            
        await session.commit()
        
        if context:
            await context.__aexit__(None, None, None)
            
    except Exception as e:
        log.error(f"Error saving batch: {e}")
        
    return count


async def _run_discovery():
    # 1. First, load seed lists to establish high priority anchors
    seeds = []
    for lst in ALL_SEED_LISTS:
        for comp in lst:
            seeds.append({
                "name": comp["name"],
                "ats_type": comp["ats_type"],
                "ats_slug": comp["ats_slug"],
                "careers_url": "", # Will be filled by enumerator updates if found
                "domain": f"{comp['ats_slug']}.com",
            })
            
    await save_companies_batch(seeds)
    log.info(f"Loaded {len(seeds)} curated seeds.")
    
    # 2. Run enumerators concurrently
    tasks = [
        enumerate_greenhouse_slugs(),
        enumerate_lever_slugs(),
        enumerate_ashby_slugs(),
        enumerate_workday_domains(),
        google_dork_discovery("greenhouse"),
        google_dork_discovery("lever"),
        google_dork_discovery("ashby"),
        google_dork_discovery("workday")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    counts = {"greenhouse": 0, "lever": 0, "ashby": 0, "workday": 0}
    all_discovered = []
    
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            log.error(f"Enumerator {idx} failed with: {result}")
            continue
            
        all_discovered.extend(result)
        for comp in result:
            ats = comp.get("ats_type")
            if ats in counts:
                counts[ats] += 1
                
    log.info(f"Enumeration finished. Saving {len(all_discovered)} potential companies...")
    
    # 3. Save to database
    inserted = await save_companies_batch(all_discovered)
    
    log.info(
        f"Discovery Task Complete! "
        f"Processed {inserted} records. "
        f"Summary: Discovered {counts['greenhouse']} greenhouse, {counts['lever']} lever, "
        f"{counts['ashby']} ashby, {counts['workday']} workday companies."
    )


@shared_task(name="discover_companies_task")
def discover_companies_task():
    """
    Celery task that runs all enumeration methods in parallel and saves to the DB.
    """
    asyncio.run(_run_discovery())

if __name__ == "__main__":
    # Configure basic logging for local testing
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run_discovery())
