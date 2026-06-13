import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    print('Total active jobs:', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE"))
    print('Active jobs (trust >= 30):', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE AND trust_score >= 30"))
    print('Active jobs (trust < 30):', await conn.fetchval("SELECT count(*) FROM jobs WHERE status='active' AND is_spam=FALSE AND trust_score < 30"))
    await conn.close()

asyncio.run(run())
