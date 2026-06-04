import asyncio
import os
import sys
from db.connection import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text('SELECT platform, scrape_status, COUNT(*) FROM discovered_companies GROUP BY platform, scrape_status ORDER BY platform'))
        for r in res.fetchall():
            print(f'{r[0]} | {r[1]} | {r[2]}')

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
