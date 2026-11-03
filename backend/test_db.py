import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    count = await conn.fetchval("SELECT count(*) FROM jobs;")
    print("TOTAL JOBS (all statuses):", count)
    status_counts = await conn.fetch("SELECT status, count(*) FROM jobs GROUP BY status;")
    print("STATUS COUNTS:", [dict(r) for r in status_counts])
    await conn.close()

asyncio.run(test())
