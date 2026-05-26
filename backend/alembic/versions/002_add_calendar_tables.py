"""add_calendar_tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add new columns to jobs table
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_open_date DATE;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS application_close_date DATE;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS hiring_cycle TEXT;")

    # 2. Create company_hiring_windows table
    op.create_table('company_hiring_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_name', sa.Text(), nullable=False),
        sa.Column('company_slug', sa.Text(), nullable=True),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('window_type', sa.Text(), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('recurrence_rule', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create indexes
    op.create_index('idx_company_hiring_windows_name', 'company_hiring_windows', ['company_name'], unique=False)
    op.create_index('idx_company_hiring_windows_date', 'company_hiring_windows', ['event_date'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_company_hiring_windows_date', table_name='company_hiring_windows')
    op.drop_index('idx_company_hiring_windows_name', table_name='company_hiring_windows')
    op.drop_table('company_hiring_windows')
    
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS application_open_date;")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS application_close_date;")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS hiring_cycle;")
