-- ─────────────────────────────────────────────────────────────────────────────
-- Placd — Schema Migration: Add company_logo_url, who_can_apply, stipend_display
-- These columns are now part of the PostgreSQL schema.sql.
-- This file is kept for documentation / audit purposes only.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. company_logo_url: URL to the company logo image
--    Populated by the Internshala detailed scraper and LinkedIn Apify scraper.
-- ALTER TABLE jobs ADD COLUMN company_logo_url TEXT DEFAULT '';

-- 2. who_can_apply: Eligibility text (e.g. "3rd year students pursuing B.Tech")
--    Extracted from Internshala detail pages. Used by eligibility_match() filter.
-- ALTER TABLE jobs ADD COLUMN who_can_apply TEXT DEFAULT '';

-- 3. stipend_display: Human-readable stipend/salary string (e.g. "₹5,000/month")
--    Preserves the exact text from the source site, separate from the numeric salary field.
-- ALTER TABLE jobs ADD COLUMN stipend_display TEXT DEFAULT '';

-- 4. last_date: Application deadline date string
--    Extracted from Internshala "Apply By" field.
-- ALTER TABLE jobs ADD COLUMN last_date TEXT DEFAULT '';

-- ─────────────────────────────────────────────────────────────────────────────
-- Index for eligibility filtering (defined in schema.sql)
-- ─────────────────────────────────────────────────────────────────────────────
-- CREATE INDEX IF NOT EXISTS idx_jobs_who_can_apply ON jobs(who_can_apply);

-- ─────────────────────────────────────────────────────────────────────────────
-- NOTE: These columns are now baked into the main schema.sql.
-- This file exists for historical reference only.
-- ─────────────────────────────────────────────────────────────────────────────
