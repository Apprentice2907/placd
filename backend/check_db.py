import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    dups = await conn.fetch("SELECT title, company_name, COUNT(*) as cnt FROM jobs WHERE status='active' GROUP BY title, company_name HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT 20")
    for row in dups:
        print(f"{row['cnt']}x: {row['title']} @ {row['company_name']}")
    
    total_active = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE status='active'")
    print(f"Total active jobs: {total_active}")
    await conn.close()

asyncio.run(run())
