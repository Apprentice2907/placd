import asyncio
import logging
from scrapers.shared.base_adapter import UnifiedAdapter

log = logging.getLogger(__name__)

class YCombinatorAdapter(UnifiedAdapter):
    source = "ycombinator"
    rpm = 30
    api_domain = "workatastartup.com"

    async def fetch_jobs(self) -> list[dict]:
        jobs = []
        try:
            # YCombinator doesn't have an easily accessible public jobs API without auth.
            # We will use an Apify actor if available, otherwise return empty.
            import os
            from apify_client import ApifyClientAsync
            
            apify_token = os.environ.get("APIFY_TOKEN")
            if not apify_token:
                log.warning("[YCombinator] No APIFY_TOKEN found. Skipping.")
                return []
                
            log.info("Using Apify for YCombinator scraping")
            client = ApifyClientAsync(apify_token)
            
            run_input = {
                "startUrls": [{"url": "https://www.workatastartup.com/companies"}],
                "maxItems": 500
            }
            
            # Note: This requires a specific Apify actor for WorkAtAStartup which may require login cookies.
            # As a fallback, we use a generic scraper if possible.
            log.warning("[YCombinator] Not fully implemented without authenticated Apify actor.")
            return []
            
        except Exception as e:
            log.error(f"[YCombinator] Scrape failed: {e}")
            return []

if __name__ == "__main__":
    adapter = YCombinatorAdapter()
    jobs = asyncio.run(adapter.run())
    print(f"Fetched {len(jobs)} jobs")
