import os
import random
import structlog
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, BrowserContext
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

from scrapers.playwright.config import PLAYWRIGHT_USER_AGENTS, PLAYWRIGHT_VIEWPORTS, STEALTH_SETTINGS

logger = structlog.get_logger(__name__)

class PlaywrightPool:
    def __init__(self, pool_size: int = 5, proxy_list: list[str] = None):
        self.pool_size = pool_size
        
        # Load proxies from env if not provided
        if proxy_list is None:
            env_proxies = os.getenv("PROXY_LIST", "")
            proxy_list = [p.strip() for p in env_proxies.split(",") if p.strip()]
            
        self.proxy_list = proxy_list
        self._current_proxy_idx = 0
        
        if not self.proxy_list:
            logger.warning("no_proxies_configured", msg="Using direct connection (dev mode).")
            
        # We don't launch browsers in __init__ because Playwright async objects
        # must be created inside the event loop where they are used.
        # Instead, we will spawn them dynamically when a context is requested.

    def _get_next_proxy(self) -> dict | None:
        if not self.proxy_list:
            return None
            
        proxy_url = self.proxy_list[self._current_proxy_idx]
        self._current_proxy_idx = (self._current_proxy_idx + 1) % len(self.proxy_list)
        
        # We need to format the proxy dict for playwright
        # 'http://user:pass@host:port' -> { 'server': 'http://host:port', 'username': 'user', 'password': 'pass' }
        try:
            # Simple parsing; in a real app, use urllib.parse
            if "@" in proxy_url:
                parts = proxy_url.split("@")
                auth = parts[0].replace("http://", "").replace("https://", "").split(":")
                server_part = parts[1]
                scheme = "https://" if proxy_url.startswith("https") else "http://"
                return {
                    "server": f"{scheme}{server_part}",
                    "username": auth[0],
                    "password": auth[1]
                }
            else:
                return {"server": proxy_url}
        except Exception as e:
            logger.error("proxy_parse_error", proxy_url=proxy_url, error=str(e))
            return None

    @asynccontextmanager
    async def get_context(self):
        """
        Yields a randomly configured BrowserContext.
        Instantiates a fresh browser session for the duration of the context.
        """
        proxy = self._get_next_proxy()
        user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)
        viewport = random.choice(PLAYWRIGHT_VIEWPORTS)
        
        async with async_playwright() as p:
            launch_args = {
                "headless": True,
                "args": ["--disable-blink-features=AutomationControlled"]
            }
            if proxy:
                launch_args["proxy"] = proxy
                
            browser = await p.chromium.launch(**launch_args)
            
            context = await browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                java_script_enabled=True,
                bypass_csp=True
            )
            
            # Apply stealth
            if stealth_async:
                # We can't stealth a context directly, we must stealth each page.
                # So we monkey-patch the new_page method for this context wrapper
                original_new_page = context.new_page
                
                async def _stealth_new_page(*args, **kwargs):
                    page = await original_new_page(*args, **kwargs)
                    await stealth_async(page)
                    return page
                    
                context.new_page = _stealth_new_page
            else:
                # Apply basic fallback stealth scripts via init_script
                await context.add_init_script(STEALTH_SETTINGS)
            
            try:
                yield context
            finally:
                await context.close()
                await browser.close()
