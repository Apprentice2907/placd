"""add profiles table

Revision ID: 003_add_profiles_table
Revises: 002_add_calendar_tables
Create Date: 2026-05-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_profiles_table'
down_revision = '002_add_calendar_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.Text(), nullable=False, unique=True),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.Text(), nullable=True),
        sa.Column('github_url', sa.Text(), nullable=True),
        sa.Column('portfolio_url', sa.Text(), nullable=True),
        sa.Column('professional_summary', sa.Text(), nullable=True),
        sa.Column('education', postgresql.JSONB(), nullable=True),
        sa.Column('experiences', postgresql.JSONB(), nullable=True),
        sa.Column('projects', postgresql.JSONB(), nullable=True),
        sa.Column('skills', postgresql.JSONB(), nullable=True),
        sa.Column('certifications', postgresql.JSONB(), nullable=True),
        sa.Column('achievements', postgresql.JSONB(), nullable=True),
        sa.Column('languages', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('profiles')
