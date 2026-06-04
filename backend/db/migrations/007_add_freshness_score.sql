-- Migration: 007_add_freshness_score

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS freshness_score FLOAT DEFAULT 1.0;
