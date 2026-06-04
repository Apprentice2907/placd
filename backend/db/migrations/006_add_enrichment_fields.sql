-- Migration 006: Add enrichment fields
-- Corresponding Alembic version: 006_add_enrichment_fields

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS enrichment_cost_usd NUMERIC(10, 4);
