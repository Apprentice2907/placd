import asyncio
import httpx
from bs4 import BeautifulSoup
import structlog
import random
from typing import List, Dict

from discovery.enumerator import save_companies_batch

logger = structlog.get_logger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

async def _fetch_html(url: str) -> str:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        logger.warning("fetch_html_failed", url=url, error=str(e))
    return ""

async def fetch_lever_public() -> List[Dict]:
    """Scrape Lever public directory if available."""
    logger.info("fetch_lever_public")
    html = await _fetch_html("https://jobs.lever.co/")
    companies = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/') and len(href) > 2:
                slug = href.strip('/')
                if slug not in ['about', 'careers', 'privacy', 'terms', 'jobs', 'blog']:
                    companies.append({
                        "name": slug.replace("-", " ").title(),
                        "ats_type": "lever",
                        "ats_slug": slug,
                        "source": "public_list"
                    })
    return companies

async def fetch_ashby_public() -> List[Dict]:
    """Scrape Ashby public directory if available."""
    logger.info("fetch_ashby_public")
    html = await _fetch_html("https://jobs.ashbyhq.com/")
    companies = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/') and len(href) > 2:
                slug = href.strip('/')
                if slug not in ['about', 'careers', 'privacy', 'terms']:
                    companies.append({
                        "name": slug.replace("-", " ").title(),
                        "ats_type": "ashby",
                        "ats_slug": slug,
                        "source": "public_list"
                    })
    return companies

async def run_public_lists():
    tasks = [
        fetch_lever_public(),
        fetch_ashby_public()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_discovered = []
    for r in results:
        if not isinstance(r, Exception):
            all_discovered.extend(r)
            
    if all_discovered:
        await save_companies_batch(all_discovered)
        logger.info("saved_public_lists", count=len(all_discovered))

if __name__ == "__main__":
    asyncio.run(run_public_lists())
