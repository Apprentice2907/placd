-- Migration 011: Add deterministic job filter tags
-- These columns power the FAANG / Remote / Internship filter tabs.
-- All values computed at save time by utils/job_tagger.py — no query-time logic needed.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_faang      BOOLEAN     DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_internship BOOLEAN     DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_hybrid     BOOLEAN     DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS work_mode     VARCHAR(10) DEFAULT 'onsite';

-- NOTE: is_remote already exists from migration 009 but may have been
-- computed from the old raw location field. Tag pipeline now owns it.
-- ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_remote BOOLEAN DEFAULT FALSE;

-- Partial indexes — only index TRUE rows to keep index tiny and fast
CREATE INDEX IF NOT EXISTS idx_jobs_faang
    ON jobs(created_at DESC)
    WHERE is_faang = TRUE AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_internship
    ON jobs(created_at DESC)
    WHERE is_internship = TRUE AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_hybrid
    ON jobs(created_at DESC)
    WHERE is_hybrid = TRUE AND status = 'active';

-- work_mode used for 3-way filter tab (remote / hybrid / onsite)
CREATE INDEX IF NOT EXISTS idx_jobs_work_mode ON jobs(work_mode, created_at DESC)
    WHERE status = 'active';

-- Composite index for "FAANG + Remote" combined filter
CREATE INDEX IF NOT EXISTS idx_jobs_faang_remote
    ON jobs(created_at DESC)
    WHERE is_faang = TRUE AND is_remote = TRUE AND status = 'active';

-- ─── Backfill note ───────────────────────────────────────────────────────────
-- For existing rows, run the Python backfill script:
--   python backend/scripts/backfill_tags.py
-- Do NOT run a raw SQL UPDATE here — it skips the tagger logic.
