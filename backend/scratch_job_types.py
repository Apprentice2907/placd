import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    counts = await conn.fetch("SELECT job_type, count(*) FROM jobs WHERE status='active' AND trust_score >= 30 AND is_spam=FALSE GROUP BY job_type")
    for r in counts:
        print(f"{r['job_type']}: {r['count']}")
    
    remote = await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND trust_score >= 30 AND is_spam=FALSE AND is_remote=TRUE")
    print("Remote count:", remote)

    intern = await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND trust_score >= 30 AND is_spam=FALSE AND is_internship=TRUE")
    print("Internship bool count:", intern)

    await conn.close()

asyncio.run(run())
