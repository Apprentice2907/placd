import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    print('Total active jobs:', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE"))
    print('Active jobs (trust >= 30):', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE AND trust_score >= 30"))
    print('Active jobs (trust < 30):', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE AND trust_score < 30"))
    await conn.close()

asyncio.run(run())
