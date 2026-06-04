"""add enrichment fields

Revision ID: 006_add_enrichment_fields
Revises: 005_add_duplicate_of
Create Date: 2026-06-03 11:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_enrichment_fields'
down_revision = '005_add_duplicate_of'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enriched_at and enrichment_cost_usd columns to jobs
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS enrichment_cost_usd NUMERIC(10, 4)")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS enrichment_cost_usd")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS enriched_at")
