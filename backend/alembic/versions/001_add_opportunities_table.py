"""add_opportunities_table

Revision ID: 001
Revises: 
Create Date: 2026-05-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure vector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table('opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('url_hash', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('opportunity_type', sa.Text(), nullable=True),
        sa.Column('funding_type', sa.Text(), nullable=True),
        sa.Column('country', sa.Text(), nullable=True),
        sa.Column('region', sa.Text(), nullable=True),
        sa.Column('organization', sa.Text(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('source_name', sa.Text(), nullable=True),
        sa.Column('source_site', sa.Text(), nullable=True),
        sa.Column('first_seen_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_verified_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('status', sa.Text(), server_default='active', nullable=True),
        # Using raw SQL for vector type to avoid depending on pgvector in Alembic directly
        sa.Column('description_embedding', sa.types.UserDefinedType(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_url'),
        sa.UniqueConstraint('url_hash')
    )
    # Re-alter column to ensure vector type is correct
    op.execute("ALTER TABLE opportunities ALTER COLUMN description_embedding TYPE vector(1536);")
    
    op.create_index('idx_opportunities_tags', 'opportunities', ['tags'], unique=False, postgresql_using='gin')
    op.create_index('idx_opportunities_url_hash', 'opportunities', ['url_hash'], unique=True)
    op.create_index('idx_opportunities_status', 'opportunities', ['status'], unique=False)
    op.create_index('idx_opportunities_type', 'opportunities', ['opportunity_type'], unique=False)

def downgrade() -> None:
    op.drop_index('idx_opportunities_type', table_name='opportunities')
    op.drop_index('idx_opportunities_status', table_name='opportunities')
    op.drop_index('idx_opportunities_url_hash', table_name='opportunities')
    op.drop_index('idx_opportunities_tags', table_name='opportunities', postgresql_using='gin')
    op.drop_table('opportunities')
