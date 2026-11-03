import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    
    print("--- UPDATING JOB TYPES ---")
    
    await conn.execute("UPDATE jobs SET job_type = 'FullTime' WHERE job_type IN ('full-time', 'full_time', 'full time', 'fulltime')")
    await conn.execute("UPDATE jobs SET job_type = 'PartTime' WHERE job_type IN ('part-time', 'part_time', 'part time', 'parttime')")
    await conn.execute("UPDATE jobs SET job_type = 'Contract' WHERE job_type IN ('contract', 'contractor')")
    await conn.execute("UPDATE jobs SET job_type = 'Internship' WHERE is_internship = TRUE OR LOWER(job_type) LIKE '%intern%'")
    await conn.execute("UPDATE jobs SET job_type = 'Remote' WHERE job_type = 'remote'")
    
    print("Updates complete.")
    await conn.close()

asyncio.run(run())
