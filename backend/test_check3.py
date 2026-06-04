import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from workers.crawlers import _crawl_discovered_company_async
from db.connection import AsyncSessionLocal
from sqlalchemy import text

async def run_inline():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT slug, platform FROM discovered_companies WHERE scrape_status = 'pending' AND platform IN ('greenhouse', 'lever', 'ashby') LIMIT 3"))
        companies = res.fetchall()
        
    for row in companies:
        print(f"Scraping {row.slug} via {row.platform}...")
        await _crawl_discovered_company_async(row.slug, row.platform)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_inline())
