import asyncio
import time
import random
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import httpx
import structlog
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, RetryCallState

from utils.redis import redis_client

logger = structlog.get_logger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; PlacdBot/1.0; +https://placd.in/bot)"

# Cache for parsed robots.txt to avoid re-fetching per domain repeatedly
_robots_cache = {}

async def can_fetch(url: str, user_agent: str = USER_AGENT) -> bool:
    """Checks robots.txt for a given URL to ensure we are allowed to scrape it."""
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{domain}/robots.txt"
    
    if domain not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            # We fetch manually to use async httpx, then pass to robotparser
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(robots_url)
                if resp.status_code in (200, 403, 401):
                    rp.parse(resp.text.splitlines())
        except Exception as e:
            logger.warning("robots_txt_fetch_failed", domain=domain, error=str(e))
            # Default to allow if robots.txt is unreachable
            rp.allow_all = True
            
        _robots_cache[domain] = rp
        
    rp = _robots_cache[domain]
    return rp.can_fetch(user_agent, url)


class RateLimitException(Exception):
    """Raised when 429 Too Many Requests is encountered."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s.")

def handle_retry_state(retry_state: RetryCallState):
    """Log retry attempts."""
    logger.warning("retrying_request", 
                   attempt=retry_state.attempt_number, 
                   exception=str(retry_state.outcome.exception()))

class StructuredBaseScraper:
    """Base class for structured scrapers, wrapping httpx with resilience."""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        after=handle_retry_state
    )
    async def make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make an HTTP request with robots.txt check, retries, exponential backoff,
        and explicit 429 Retry-After handling.
        """
        # Ensure User-Agent is set
        headers = kwargs.pop("headers", {})
        if "User-Agent" not in headers:
            headers["User-Agent"] = USER_AGENT
            
        if not await can_fetch(url, headers.get("User-Agent")):
            logger.warning("robots_txt_disallowed", url=url)
            raise ValueError(f"robots.txt disallowed fetching: {url}")
            
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                duration = time.time() - start_time
                
                logger.info("http_request", 
                            method=method, 
                            url=url, 
                            status_code=response.status_code, 
                            duration_s=round(duration, 3))
                            
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    jitter = random.uniform(1.0, 3.0)
                    total_wait = retry_after + jitter
                    logger.warning("rate_limited_429", url=url, retry_after=total_wait)
                    await asyncio.sleep(total_wait)
                    raise RateLimitException(int(total_wait))
                    
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                # We do not retry on 404 or 400 errors usually, but 429 is handled above.
                if e.response.status_code >= 500:
                    raise e # Retried by tenacity
                else:
                    logger.warning("http_client_error", url=url, status_code=e.response.status_code)
                    raise e

    async def enqueue_playwright_fallback(self, domain: str):
        """If a structured attempt fails fully, add the domain to a Redis queue for Playwright."""
        try:
            await redis_client.lpush("playwright_queue", domain)
            logger.info("enqueued_playwright_fallback", domain=domain)
        except Exception as e:
            logger.error("enqueue_playwright_failed", domain=domain, error=str(e))
