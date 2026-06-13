import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    counts = await conn.fetch("SELECT status, trust_score >= 30 as is_trusted, count(*) FROM jobs WHERE is_spam = FALSE GROUP BY status, is_trusted")
    print('Breakdown:', counts)
    await conn.close()

asyncio.run(run())
