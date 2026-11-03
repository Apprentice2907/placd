import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    counts = await conn.fetch("SELECT status, trust_score >= 30 as is_trusted, count(*) FROM jobs WHERE is_spam = FALSE GROUP BY status, is_trusted")
    print('Breakdown:', counts)
    await conn.close()

asyncio.run(run())
