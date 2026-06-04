"""add discovered_companies

Revision ID: 008_discovered_companies
Revises: 007_add_freshness_score
Create Date: 2026-06-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_discovered_companies'
down_revision = '007_add_freshness_score'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS discovered_companies (
        id SERIAL PRIMARY KEY,
        slug VARCHAR(200) NOT NULL,
        platform VARCHAR(50) NOT NULL,
        source VARCHAR(50) NOT NULL,
        first_seen_at TIMESTAMPTZ DEFAULT NOW(),
        last_scraped_at TIMESTAMPTZ,
        scrape_status VARCHAR(20) DEFAULT 'pending',
        job_count_last INT DEFAULT 0,
        UNIQUE(slug, platform)
    );
    CREATE INDEX IF NOT EXISTS idx_discovered_pending ON discovered_companies(platform, scrape_status) 
    WHERE scrape_status = 'pending';
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS discovered_companies;")
