-- Migration 005: Add duplicate_of column
-- Corresponding Alembic version: 005_add_duplicate_of

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_of VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_of ON jobs(duplicate_of);
