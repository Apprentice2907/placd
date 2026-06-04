import asyncio
import sys
from db.connection import engine
from sqlalchemy import text

async def run():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE jobs ALTER COLUMN duplicate_of TYPE TEXT USING duplicate_of::TEXT;'))

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
