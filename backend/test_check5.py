import asyncio
import sys
from db.connection import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT source, COUNT(*), MAX(created_at) as latest FROM jobs WHERE status = 'active' GROUP BY source ORDER BY COUNT(*) DESC"))
        for r in res.fetchall():
            print(f'{r[0]} | count: {r[1]} | latest: {r[2]}')

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
