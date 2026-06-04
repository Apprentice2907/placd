-- Migration 010: Add company enrichment columns to jobs table

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_logo_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company_domain TEXT;

-- Index for logo enrichment queue (find jobs needing logos)
CREATE INDEX IF NOT EXISTS idx_jobs_needs_logo ON jobs(created_at DESC)
  WHERE company_logo_url IS NULL AND status = 'active' AND is_spam = FALSE;
