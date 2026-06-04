"""add duplicate_of column

Revision ID: 005_add_duplicate_of
Revises: 004_new_scrapers_and_indexes
Create Date: 2026-06-03 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_duplicate_of'
down_revision = '004_new_scrapers_and_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add duplicate_of column to jobs
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_of VARCHAR(50)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_of ON jobs(duplicate_of)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_jobs_duplicate_of")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS duplicate_of")
