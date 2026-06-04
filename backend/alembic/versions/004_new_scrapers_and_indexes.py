"""add source_platform, skills_raw columns and new indexes

Revision ID: 004_new_scrapers_and_indexes
Revises: 003_add_profiles_table
Create Date: 2026-06-03 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_new_scrapers_and_indexes'
down_revision = '003_add_profiles_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add source_platform column
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source_platform ON jobs(source_platform)")

    # 2. HNSW index for vector search (much faster than IVFFlat at query time)
    #    Using op.execute for CREATE INDEX CONCURRENTLY — must run outside a transaction.
    #    Alembic wraps each migration in a transaction by default; to support CONCURRENTLY
    #    we'd need non-transactional DDL mode. For safety, we use the non-concurrent form
    #    which works inside a transaction. If running in production with large data,
    #    consider running the CONCURRENTLY variant manually.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw
        ON jobs USING hnsw (description_embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)
    """)

    # 3. Partial index for active jobs only (speeds up the most common query)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_active
        ON jobs (created_at DESC) WHERE status = 'active'
    """)

    # 4. skills_raw JSONB column
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills_raw JSONB")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_skills_raw ON jobs USING GIN(skills_raw)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_jobs_skills_raw")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS skills_raw")

    op.execute("DROP INDEX IF EXISTS idx_jobs_active")
    op.execute("DROP INDEX IF EXISTS idx_jobs_embedding_hnsw")

    op.execute("DROP INDEX IF EXISTS idx_jobs_source_platform")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS source_platform")
