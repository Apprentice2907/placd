import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb')
    
    print("--- 1. CHECKING INDEXES ---")
    indexes = await conn.fetch("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'jobs' ORDER BY indexname")
    for idx in indexes:
        print(f"INDEX: {idx['indexname']} -> {idx['indexdef']}")

    print("\n--- 2. DROPPING BAD INDEX ---")
    # In the last session I created: uq_jobs_title_company
    try:
        await conn.execute("DROP INDEX IF EXISTS uq_jobs_title_company")
        print("Dropped uq_jobs_title_company")
    except Exception as e:
        print("Failed to drop index:", e)

    print("\n--- 3. FINDING TRUE DUPLICATES (url_hash) ---")
    url_dups = await conn.fetch("""
        SELECT url_hash, COUNT(*) FROM jobs 
        GROUP BY url_hash HAVING COUNT(*) > 1
    """)
    print("True duplicates (url_hash > 1):", len(url_dups))

    print("\n--- 4. FINDING NEAR DUPLICATES ---")
    near_dups = await conn.fetch("""
        SELECT title, company_name, location, job_type, COUNT(*) as cnt
        FROM jobs 
        GROUP BY title, company_name, location, job_type 
        HAVING COUNT(*) > 1 
        ORDER BY COUNT(*) DESC 
        LIMIT 20
    """)
    for row in near_dups:
        print(f"{row['cnt']}x: {row['title']} @ {row['company_name']} ({row['location']}) - {row['job_type']}")

    print("\n--- 5. DELETING NEAR DUPLICATES ---")
    # Using CAST(a.id AS text) < CAST(b.id AS text) since timestamps might be identical
    deleted = await conn.execute("""
        DELETE FROM jobs a USING jobs b
        WHERE a.title = b.title
          AND a.company_name = b.company_name
          AND COALESCE(a.location, '') = COALESCE(b.location, '')
          AND COALESCE(a.job_type, '') = COALESCE(b.job_type, '')
          AND CAST(a.id AS text) < CAST(b.id AS text)
    """)
    print("Deleted near duplicates:", deleted)

    await conn.close()

asyncio.run(run())
