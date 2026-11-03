import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    
    print("--- JOB TYPES ---")
    res1 = await conn.fetch("SELECT job_type, COUNT(*) FROM jobs WHERE status = 'active' GROUP BY job_type ORDER BY count DESC")
    for r in res1:
        print(f"{r['job_type']}: {r['count']}")
        
    print("\n--- INTERNSHIPS ---")
    res = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE status = 'active' AND (is_internship = TRUE OR LOWER(job_type) = 'internship')")
    print(f"Final Count for Internships: {res}")

    await conn.close()

asyncio.run(run())
