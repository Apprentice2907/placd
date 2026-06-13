import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    
    print("--- JOB TYPES ---")
    res1 = await conn.fetch("SELECT job_type, COUNT(*) FROM jobs WHERE status = 'active' GROUP BY job_type ORDER BY count DESC")
    for r in res1:
        print(f"{r['job_type']}: {r['count']}")
        
    print("\n--- INTERNSHIPS ---")
    res = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND (is_internship = TRUE OR LOWER(job_type) = 'internship')")
    print(f"Final Count for Internships: {res}")

    await conn.close()

asyncio.run(run())
