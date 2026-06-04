-- Migration 004: New scrapers support — columns and indexes
-- Corresponding Alembic version: 004_new_scrapers_and_indexes

-- 1. Add source_platform column
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_jobs_source_platform ON jobs(source_platform);

-- 2. HNSW index for vector search (much faster than IVFFlat at query time)
CREATE INDEX IF NOT EXISTS idx_jobs_embedding_hnsw
ON jobs USING hnsw (description_embedding vector_cosine_ops)
WITH (m=16, ef_construction=64);

-- 3. Partial index for active jobs only
CREATE INDEX IF NOT EXISTS idx_jobs_active
ON jobs (created_at DESC) WHERE status = 'active';

-- 4. skills_raw JSONB column
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills_raw JSONB;
CREATE INDEX IF NOT EXISTS idx_jobs_skills_raw ON jobs USING GIN(skills_raw);
