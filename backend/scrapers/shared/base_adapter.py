"""
Placd — Unified Adapter Base Class

All ATS scrapers inherit from UnifiedAdapter. Provides:
  - httpx.AsyncClient with UA rotation (from politeness.UA_POOL)
  - Per-domain token-bucket rate limiting (DomainRateLimiter)
  - Exponential backoff with jitter on 429/503 (Retry-After aware)
  - Circuit breaker integration (per source domain)
  - robots.txt compliance check before scraping
  - save_to_db() — PG upsert via url_hash
  - run() — orchestrates robots check → circuit breaker → fetch → save → log
"""

import asyncio
import hashlib
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import text
from db.connection import AsyncSessionLocal

from scrapers.shared.politeness import (
    domain_limiter,
    robots_txt_allowed,
    UA_POOL,
)
from scrapers.shared.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
)

logger = logging.getLogger(__name__)


class ScraperException(Exception):
    """Exception raised for errors during scraping."""
    pass


class UnifiedAdapter(ABC):
    source: str = ""
    company: str = ""
    rpm: int = 60
    # The canonical API domain for this ATS type.  Override in subclass.
    api_domain: str = ""

    def __init__(self, company_config: dict = None):
        self.company_config = company_config or {}
        if not self.company:
            self.company = self.company_config.get("name", self.company)
        self.priority = self.company_config.get("priority", 10)
        self.tags = self.company_config.get("tags", [])
        self.company_type = self.company_config.get("company_type", "")
        self.board_token = self.company_config.get("board_token", "")

        # Circuit breaker — one per api_domain (or source as fallback)
        cb_domain = self.api_domain or self.source or "unknown"
        self._circuit_breaker = CircuitBreaker(domain=cb_domain)

    def _format_tags(self) -> str:
        return ", ".join(self.tags) if self.tags else ""

    # ── HTTP Client ──────────────────────────────────────────────────────

    def get_client(self) -> httpx.AsyncClient:
        """Get an AsyncClient with a randomly-rotated User-Agent."""
        headers = {
            "User-Agent": random.choice(UA_POOL),
            "Accept": "application/json, text/html, application/xhtml+xml, application/xml",
        }
        return httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True)

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """
        Fetch URL with:
          1. Per-domain rate-limit token acquisition
          2. Exponential backoff + jitter on 429/503
          3. Retry-After header respect
        """
        max_retries = 3
        base_wait = 2.0
        max_wait = 60.0

        # Extract domain for rate-limiter
        parsed = urlparse(url)
        domain = parsed.hostname or ""

        for attempt in range(max_retries + 1):
            # Acquire a rate-limit token for this domain
            await domain_limiter.acquire(domain)

            try:
                response = await client.get(url, **kwargs)

                if response.status_code in (429, 503):
                    if attempt == max_retries:
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = float(retry_after)
                    else:
                        wait_time = min(max_wait, base_wait * (2 ** attempt)) + random.uniform(0, 1)

                    logger.warning(
                        "rate_limited",
                        status=response.status_code,
                        url=url,
                        retry_in=f"{wait_time:.2f}s",
                    )
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code not in (429, 503) and e.response.status_code < 500:
                    logger.error(f"HTTP error {e.response.status_code} fetching {url}: {e}", exc_info=True)
                    raise ScraperException(f"HTTP error {e.response.status_code}: {e}") from e

                if attempt == max_retries:
                    logger.error(f"Failed to fetch {url} after {max_retries} retries: {e}", exc_info=True)
                    raise ScraperException(f"Failed after {max_retries} retries: {e}") from e

                wait_time = min(max_wait, base_wait * (2 ** attempt)) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)

            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Request failed for {url}: {e}", exc_info=True)
                    raise ScraperException(f"Request failed: {e}") from e

                wait_time = min(max_wait, base_wait * (2 ** attempt)) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)

        raise ScraperException(f"Exhausted retries for {url}")

    # ── Abstract ─────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs logic to be implemented by subclass."""
        pass

    # ── Persistence ──────────────────────────────────────────────────────

    async def save_to_db(self, jobs: List[Dict[str, Any]]) -> int:
        """Upserts jobs into PostgreSQL database via url_hash."""
        from db.database import async_save_jobs
        
        inserted, updated = await async_save_jobs(jobs=jobs, source=self.source)
        return inserted

    # ── Orchestrator ─────────────────────────────────────────────────────

    def _build_probe_url(self) -> str:
        """
        Return a representative URL for this adapter's API.
        Used for robots.txt checking.  Override if the ATS URL
        pattern differs from the default.
        """
        if self.api_domain:
            return f"https://{self.api_domain}/"
        return ""

    async def run(self) -> List[Dict[str, Any]]:
        """
        Main execution flow:
          1. robots.txt check
          2. Circuit breaker guard
          3. fetch_jobs()
          4. save_to_db()
          5. Structured logging
        """
        start_time = time.time()
        jobs: List[Dict[str, Any]] = []

        # ── 1. robots.txt ────────────────────────────────────────────────
        probe_url = self._build_probe_url()
        if probe_url:
            ua = random.choice(UA_POOL)
            allowed = await robots_txt_allowed(probe_url, user_agent=ua)
            if not allowed:
                logger.warning(
                    "robots_txt_disallowed",
                    source=self.source,
                    company=self.company,
                    url=probe_url,
                )
                return jobs

        # ── 2 + 3. Circuit breaker wraps fetch_jobs() ────────────────────
        try:
            jobs = await self._circuit_breaker.call(self.fetch_jobs())

            # ── 4. Save ──────────────────────────────────────────────────
            inserted = await self.save_to_db(jobs)

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "scraper_success",
                source=self.source,
                company=self.company,
                job_count=len(jobs),
                inserted=inserted,
                duration_ms=duration_ms,
            )

        except CircuitOpenError as coe:
            logger.warning(
                "scraper_circuit_open",
                source=self.source,
                company=self.company,
                retry_after=f"{coe.retry_after:.0f}s",
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "scraper_failure",
                source=self.source,
                company=self.company,
                error=str(e),
                duration_ms=duration_ms,
                exc_info=True,
            )

        return jobs
