-- Migration 009: Add trust score and spam columns to jobs table
-- Supports the quality filtering layer

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS trust_score INT DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_spam BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS spam_reason VARCHAR(200);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_tier INT DEFAULT 0;

-- Index for sorting by trust (featured jobs, quality search)
CREATE INDEX IF NOT EXISTS idx_jobs_trust_score ON jobs(trust_score DESC);

-- Partial index for featured jobs (trust >= 80, active)
CREATE INDEX IF NOT EXISTS idx_jobs_featured ON jobs(trust_score DESC)
  WHERE trust_score >= 80 AND status = 'active';

-- Partial index to quickly skip spam
CREATE INDEX IF NOT EXISTS idx_jobs_not_spam ON jobs(created_at DESC)
  WHERE is_spam = FALSE AND status = 'active';
