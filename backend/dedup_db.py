import os
from dotenv import load_dotenv

load_dotenv()

import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    
    # 1. Delete duplicates keeping the most recently created one
    deleted = await conn.execute("""
        DELETE FROM jobs a USING jobs b
        WHERE a.title = b.title 
          AND a.company_name = b.company_name 
          AND a.created_at < b.created_at
    """)
    print("Deleted duplicates:", deleted)
    
    # 2. Add Unique constraint
    try:
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_title_company 
            ON jobs (title, company_name)
        """)
        print("Unique index created successfully.")
    except Exception as e:
        print("Error creating unique index:", e)

    await conn.close()

asyncio.run(run())
