"""
Backfill company_name for Ashby jobs by extracting company name from the Ashby API slug.
Ashby job URLs look like: https://jobs.ashbyhq.com/{company-slug}/...
We extract the slug and use it as the company name.
"""
import asyncio
import asyncpg

NEON_URL = "postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb"

async def backfill():
    conn = await asyncpg.connect(NEON_URL)
    
    # For Ashby jobs: URL format is https://jobs.ashbyhq.com/{slug}/{job-id}/application
    # Extract slug as company name
    updated = await conn.execute("""
        UPDATE jobs
        SET 
            company_name = INITCAP(REPLACE(SPLIT_PART(apply_url, '/', 4), '-', ' ')),
            company_logo_url = 'https://logo.clearbit.com/' || SPLIT_PART(apply_url, '/', 4) || '.com',
            company_domain = SPLIT_PART(apply_url, '/', 4) || '.com'
        WHERE source = 'ashby'
        AND company_name IS NULL
        AND apply_url LIKE '%ashbyhq.com%'
        AND SPLIT_PART(apply_url, '/', 4) != '';
    """)
    print(f"Backfilled Ashby company names: {updated}")
    
    # Verify
    still_missing = await conn.fetchval("SELECT count(*) FROM jobs WHERE company_name IS NULL AND status = 'active';")
    print(f"Still missing company_name: {still_missing}")
    
    # Sample 3 to verify
    samples = await conn.fetch("SELECT title, company_name, company_logo_url, company_domain FROM jobs WHERE source = 'ashby' AND status = 'active' LIMIT 5;")
    for r in samples:
        print(dict(r))
    
    await conn.close()
    print("Done!")

asyncio.run(backfill())
