import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    
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
