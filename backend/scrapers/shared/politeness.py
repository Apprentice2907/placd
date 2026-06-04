"""
Placd — Politeness Layer

Provides per-domain rate limiting, robots.txt compliance checking,
and a pool of realistic user-agent strings.

All rate-limit state is in-memory (per-process token buckets).
robots.txt results are cached in Redis with 24h TTL.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# ─── Redis Client (shared) ──────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
_redis_client: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    """Lazy-init a module-level async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ─── Per-Domain RPM Limits ───────────────────────────────────────────────────

DOMAIN_RPM: Dict[str, int] = {
    "greenhouse.io": 60,
    "lever.co": 60,
    "ashby.com": 100,
    "workable.com": 60,
    "bamboohr.com": 30,
    "recruitee.com": 30,
    "himalayas.app": 20,
    "cutshort.io": 20,
    "instahyre.com": 10,
    "naukri.com": 10,
    "linkedin.com": 5,
    "wellfound.com": 5,
    "internshala.com": 15,
}

DEFAULT_RPM = 20


def _match_domain_rpm(domain: str) -> int:
    """
    Match a full hostname against DOMAIN_RPM keys.
    E.g. 'boards-api.greenhouse.io' matches 'greenhouse.io'.
    """
    domain_lower = domain.lower()
    for key, rpm in DOMAIN_RPM.items():
        if domain_lower == key or domain_lower.endswith("." + key):
            return rpm
    return DEFAULT_RPM


# ─── Token Bucket Rate Limiter ───────────────────────────────────────────────

class _DomainBucket:
    """In-memory token bucket for a single domain."""

    __slots__ = ("rpm", "tokens", "last_refill")

    def __init__(self, rpm: int):
        self.rpm = rpm
        self.tokens: float = rpm  # start full
        self.last_refill: float = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.rpm, self.tokens + elapsed * (self.rpm / 60.0))
        self.last_refill = now


class DomainRateLimiter:
    """
    Asyncio-native per-domain token bucket rate limiter.

    Usage::

        limiter = DomainRateLimiter()
        await limiter.acquire("boards-api.greenhouse.io")
        # … make request …
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, _DomainBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, domain: str) -> _DomainBucket:
        if domain not in self._buckets:
            rpm = _match_domain_rpm(domain)
            self._buckets[domain] = _DomainBucket(rpm)
        return self._buckets[domain]

    async def acquire(self, domain: str) -> None:
        """
        Wait until a token is available for *domain*, then consume it.
        """
        async with self._lock:
            bucket = self._get_bucket(domain)
            bucket._refill()

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return

            # Need to wait for one token
            deficit = 1.0 - bucket.tokens
            wait_secs = deficit * (60.0 / bucket.rpm)

        # Sleep outside the lock so other domains aren't blocked
        await asyncio.sleep(wait_secs)

        async with self._lock:
            bucket = self._get_bucket(domain)
            bucket._refill()
            bucket.tokens = max(0.0, bucket.tokens - 1.0)


# Module-level singleton
domain_limiter = DomainRateLimiter()


# ─── robots.txt Compliance ───────────────────────────────────────────────────

_ROBOTS_TTL = 86400  # 24 hours


async def robots_txt_allowed(url: str, user_agent: str = "*") -> bool:
    """
    Check whether *url* is allowed by the site's robots.txt.

    Results are cached in Redis for 24 hours per (domain, user_agent).
    On any fetch failure the function defaults to **True** (allow).
    """
    parsed = urlparse(url)
    domain = parsed.hostname or ""
    if not domain:
        return True

    cache_key = f"robots:{domain}:{user_agent}"

    # 1. Try Redis cache
    try:
        r = await _get_redis()
        cached = await r.get(cache_key)
        if cached is not None:
            # "1" = allowed whole site, "0" = disallowed whole site
            # For per-path granularity we store the raw robots.txt text
            if cached in ("1", "0"):
                return cached == "1"
            # cached is the raw robots.txt content — parse it
            rp = RobotFileParser()
            rp.parse(cached.splitlines())
            return rp.can_fetch(user_agent, url)
    except Exception:
        pass  # Redis down — fall through

    # 2. Fetch robots.txt
    robots_url = f"{parsed.scheme}://{domain}/robots.txt"
    robots_text: Optional[str] = None

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                robots_text = resp.text
    except Exception:
        pass

    if robots_text is None:
        # Could not fetch — default to allowed, cache positive
        try:
            r = await _get_redis()
            await r.setex(cache_key, _ROBOTS_TTL, "1")
        except Exception:
            pass
        return True

    # 3. Parse and check
    rp = RobotFileParser()
    rp.parse(robots_text.splitlines())
    allowed = rp.can_fetch(user_agent, url)

    # 4. Cache the raw text for future per-path lookups
    try:
        r = await _get_redis()
        await r.setex(cache_key, _ROBOTS_TTL, robots_text)
    except Exception:
        pass

    return allowed


# ─── User-Agent Pool ─────────────────────────────────────────────────────────

UA_POOL = [
    # Chrome — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome — macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome — Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox — macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Firefox — Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari — macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Edge — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]
