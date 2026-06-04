-- Migration: 008_discovered_companies

CREATE TABLE IF NOT EXISTS discovered_companies (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(200) NOT NULL,
    platform VARCHAR(50) NOT NULL,  -- greenhouse, lever, ashby, workday, bamboohr
    source VARCHAR(50) NOT NULL,    -- commoncrawl, google_dork, manual
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at TIMESTAMPTZ,
    scrape_status VARCHAR(20) DEFAULT 'pending',  -- pending, active, dead
    job_count_last INT DEFAULT 0,
    UNIQUE(slug, platform)
);

CREATE INDEX IF NOT EXISTS idx_discovered_pending ON discovered_companies(platform, scrape_status) 
WHERE scrape_status = 'pending';
