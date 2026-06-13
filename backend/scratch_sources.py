import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    counts = await conn.fetch("SELECT source, count(*) FROM jobs WHERE status='active' GROUP BY source")
    print("Sources:")
    for row in counts:
        print(f"- {row['source']}: {row['count']}")
    await conn.close()

asyncio.run(run())
