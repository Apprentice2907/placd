import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    count = await conn.fetchval("SELECT count(*) FROM jobs;")
    print("TOTAL JOBS (all statuses):", count)
    status_counts = await conn.fetch("SELECT status, count(*) FROM jobs GROUP BY status;")
    print("STATUS COUNTS:", [dict(r) for r in status_counts])
    await conn.close()

asyncio.run(test())
