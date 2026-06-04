import asyncio
import sys
from db.connection import engine
from sqlalchemy import text

async def run():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_of UUID;'))
        await conn.execute(text('ALTER TABLE jobs ADD COLUMN IF NOT EXISTS freshness_score FLOAT DEFAULT 0.0;'))

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
