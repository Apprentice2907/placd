"""add freshness score

Revision ID: 007_add_freshness_score
Revises: 006_add_enrichment_fields
Create Date: 2026-06-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_freshness_score'
down_revision = '006_add_enrichment_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We execute raw SQL since we manage migrations as SQL files in this repo usually
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS freshness_score FLOAT DEFAULT 1.0;")

def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF NOT EXISTS freshness_score;")
