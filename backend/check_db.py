import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    dups = await conn.fetch("SELECT title, company_name, COUNT(*) as cnt FROM jobs WHERE status='active' GROUP BY title, company_name HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT 20")
    for row in dups:
        print(f"{row['cnt']}x: {row['title']} @ {row['company_name']}")
    
    total_active = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE status='active'")
    print(f"Total active jobs: {total_active}")
    await conn.close()

asyncio.run(run())
