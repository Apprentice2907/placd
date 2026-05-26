import abc
import asyncio
import random
import logging
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

import sys
from pathlib import Path

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from db.connection import AsyncSessionLocal
from models import Opportunity

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.15"
]

class BaseOpportunityScraper(abc.ABC):
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    async def _close(self):
        await self.client.aclose()

    async def fetch_html(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL with retries, jitter, and realistic user agent."""
        max_retries = 3
        for attempt in range(max_retries):
            # Jitter 0.5-1.5s
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            try:
                logger.info(f"[{self.source_name}] Fetching {url} (Attempt {attempt+1})")
                response = await self.client.get(url, headers=headers)
                
                if response.status_code in (429, 503, 502):
                    logger.warning(f"[{self.source_name}] Rate limited {response.status_code} on {url}. Backing off.")
                    await asyncio.sleep((2 ** attempt) + random.uniform(1, 3))
                    continue
                
                if response.status_code == 404:
                    logger.info(f"[{self.source_name}] 404 Not Found: {url}")
                    return None
                    
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
                
            except httpx.HTTPError as e:
                logger.error(f"[{self.source_name}] HTTP error on {url}: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep((2 ** attempt) + random.uniform(1, 3))
                
        return None

    async def fetch_listing_page(self, url: str, page: int = 1) -> Optional[BeautifulSoup]:
        """Handles WordPress pagination: ?page=N or /page/N/ pattern."""
        page_url = url
        if page > 1:
            if "?" in url:
                page_url = f"{url}&page={page}"
            else:
                base = url.rstrip("/")
                page_url = f"{base}/page/{page}/"
        return await self.fetch_html(page_url)

    async def get_all_listing_urls(self, category_url: str) -> List[str]:
        """
        Crawls a category, paginating until no new links are found.
        Override if pagination logic differs.
        """
        all_urls = set()
        page = 1
        consecutive_empty_pages = 0
        
        while page <= 500:
            soup = await self.fetch_listing_page(category_url, page)
            if not soup:
                break
                
            new_urls = self.extract_links_from_listing(soup)
            if not new_urls:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:
                    break
            else:
                consecutive_empty_pages = 0
                
            added_any = False
            for url in new_urls:
                if url not in all_urls:
                    all_urls.add(url)
                    added_any = True
            
            if not added_any:
                break # Reached a page where we've seen all links before
                
            page += 1
            
        return list(all_urls)

    @abc.abstractmethod
    def extract_links_from_listing(self, soup: BeautifulSoup) -> List[str]:
        """Extract individual post URLs from a listing page soup."""
        pass

    @abc.abstractmethod
    async def scrape_post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetches individual post page, returns structured dict or None on failure."""
        pass

    @abc.abstractmethod
    async def crawl_category(self, category_slug: str, **kwargs) -> List[Dict[str, Any]]:
        """Crawl an entire category and return records."""
        pass

    async def upsert_opportunities(self, records: List[Dict[str, Any]]):
        """
        Upsert into opportunities table using url_hash for dedup.
        Log to crawl_log table.
        """
        if not records:
            logger.info(f"[{self.source_name}] No records to upsert.")
            return

        import hashlib
        
        records_found = len(records)
        records_new = 0
        records_updated = 0
        
        start_time = asyncio.get_event_loop().time()

        async with AsyncSessionLocal() as session:
            for rec in records:
                source_url = rec.get("source_url")
                if not source_url:
                    continue
                    
                url_hash = hashlib.sha256(source_url.encode('utf-8')).hexdigest()
                
                # Check if exists
                stmt = sa.select(Opportunity.id).where(Opportunity.url_hash == url_hash)
                result = await session.execute(stmt)
                existing_id = result.scalar()
                
                if existing_id:
                    # Update
                    update_stmt = sa.update(Opportunity).where(Opportunity.id == existing_id).values(
                        title=rec.get("title"),
                        description=rec.get("description"),
                        opportunity_type=rec.get("opportunity_type"),
                        funding_type=rec.get("funding_type"),
                        country=rec.get("country"),
                        region=rec.get("region"),
                        organization=rec.get("organization"),
                        deadline=rec.get("deadline"),
                        start_date=rec.get("start_date"),
                        tags=rec.get("tags", []),
                        last_verified_at=sa.func.now(),
                        status='active'
                    )
                    await session.execute(update_stmt)
                    records_updated += 1
                else:
                    # Insert
                    new_opp = Opportunity(
                        source_url=source_url,
                        url_hash=url_hash,
                        title=rec.get("title", ""),
                        description=rec.get("description"),
                        opportunity_type=rec.get("opportunity_type"),
                        funding_type=rec.get("funding_type"),
                        country=rec.get("country"),
                        region=rec.get("region"),
                        organization=rec.get("organization"),
                        deadline=rec.get("deadline"),
                        start_date=rec.get("start_date"),
                        tags=rec.get("tags", []),
                        source_name=self.source_name,
                        source_site=self.base_url,
                        last_verified_at=sa.func.now(),
                        status='active'
                    )
                    session.add(new_opp)
                    records_new += 1
                    
            await session.commit()
            
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Log to crawl_log
            try:
                log_stmt = text("""
                    INSERT INTO crawl_log (source, jobs_found, jobs_new, duration_ms)
                    VALUES (:source, :found, :new, :duration)
                """)
                await session.execute(log_stmt, {
                    "source": self.source_name,
                    "found": records_found,
                    "new": records_new,
                    "duration": duration_ms
                })
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to write crawl log: {e}")
                
        logger.info(f"[{self.source_name}] Upsert complete. Found: {records_found}, New: {records_new}, Updated: {records_updated}")
