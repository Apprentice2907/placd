import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    counts = await conn.fetch("SELECT source, count(*) FROM jobs WHERE status='active' GROUP BY source")
    print("Sources:")
    for row in counts:
        print(f"- {row['source']}: {row['count']}")
    await conn.close()

asyncio.run(run())
