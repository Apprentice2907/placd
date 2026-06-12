"""
Migration: Add GIN search_vector column + company_name/logo columns to jobs table.
Run once against Neon to get immediate FTS performance improvement.
"""
import asyncio
import asyncpg

NEON_URL = "postgresql://neondb_owner:npg_Ki9wP2nSAkzs@ep-orange-cake-at8squfa.c-9.us-east-1.aws.neon.tech/neondb"

MIGRATION_SQL = [
    # 1. Add company_name and logo columns so we don't need joins for every card
    """
    ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS company_name TEXT,
    ADD COLUMN IF NOT EXISTS company_logo_url TEXT,
    ADD COLUMN IF NOT EXISTS company_domain TEXT
    """,
    # 2. Backfill any existing company data from companies table
    """
    UPDATE jobs j
    SET
        company_name = c.name,
        company_logo_url = c.logo_url,
        company_domain = c.domain
    FROM companies c
    WHERE j.company_id = c.id
    AND j.company_name IS NULL
    """,
    # 3. Add the stored tsvector column for fast FTS
    """
    ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(title, '') || ' ' ||
                coalesce(company_name, '') || ' ' ||
                coalesce(description, '')
            )
        ) STORED
    """,
    # 4. GIN index on the search_vector
    """
    CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING GIN(search_vector)
    """,
    # 5. Composite index for the main listing query
    """
    CREATE INDEX IF NOT EXISTS idx_jobs_active_trust ON jobs(status, trust_score DESC)
    WHERE status = 'active' AND is_spam = FALSE
    """,
]


async def run_migration():
    print("Connecting to Neon...")
    conn = await asyncpg.connect(NEON_URL)
    for i, sql in enumerate(MIGRATION_SQL, 1):
        print(f"Running step {i}/{len(MIGRATION_SQL)}...")
        try:
            await conn.execute(sql.strip())
            print(f"  [OK] Step {i} done")
        except Exception as e:
            print(f"  [SKIP] Step {i} error (may be OK if already exists): {e}")
    
    # Verify
    count = await conn.fetchval("SELECT count(*) FROM jobs WHERE search_vector IS NOT NULL;")
    print(f"\nVerification: {count} jobs have search_vector populated")
    await conn.close()
    print("Migration complete!")


asyncio.run(run_migration())
