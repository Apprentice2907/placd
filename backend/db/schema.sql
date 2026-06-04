CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS discovered_companies (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(200) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at TIMESTAMPTZ,
    scrape_status VARCHAR(20) DEFAULT 'pending',
    job_count_last INT DEFAULT 0,
    UNIQUE(slug, platform)
);
CREATE INDEX IF NOT EXISTS idx_discovered_pending ON discovered_companies(platform, scrape_status) 
WHERE scrape_status = 'pending';

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT UNIQUE,
    ats_type TEXT,
    ats_slug TEXT,
    careers_url TEXT,
    logo_url TEXT,
    size_tier TEXT,
    country TEXT DEFAULT 'US',
    crawl_priority INTEGER DEFAULT 5,
    crawl_status TEXT DEFAULT 'pending',
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    external_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    description_embedding vector(1536),
    apply_url TEXT NOT NULL,
    source TEXT,
    job_type TEXT,
    location TEXT,
    is_remote BOOLEAN DEFAULT FALSE,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    experience_level TEXT,
    tags TEXT[],
    categories TEXT[],
    status TEXT DEFAULT 'active',
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    url_hash TEXT UNIQUE,
    content_hash TEXT,
    duplicate_of TEXT,
    application_open_date DATE,
    hiring_cycle TEXT,
    enriched_at TIMESTAMPTZ,
    enrichment_cost_usd NUMERIC(10, 4) DEFAULT 0.0,
    freshness_score FLOAT DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id),
    source TEXT,
    source_url TEXT,
    seen_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawl_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    source TEXT,
    jobs_found INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_expired INTEGER DEFAULT 0,
    error TEXT,
    duration_ms INTEGER,
    crawled_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_is_remote ON jobs(is_remote);
CREATE INDEX IF NOT EXISTS idx_jobs_categories ON jobs USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_jobs_last_verified_at ON jobs(last_verified_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_url_hash ON jobs(url_hash);
-- Note: ivfflat index requires creating the index with a specific operator class (e.g. vector_l2_ops)
CREATE INDEX IF NOT EXISTS idx_jobs_description_embedding ON jobs USING ivfflat (description_embedding vector_l2_ops);
CREATE INDEX IF NOT EXISTS idx_companies_ats_type ON companies(ats_type);
CREATE INDEX IF NOT EXISTS idx_companies_crawl_status ON companies(crawl_status);

CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT UNIQUE NOT NULL,
    url_hash TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    opportunity_type TEXT,
    funding_type TEXT,
    country TEXT,
    region TEXT,
    organization TEXT,
    deadline DATE,
    start_date DATE,
    tags TEXT[],
    source_name TEXT,
    source_site TEXT,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    description_embedding vector(1536)
);
CREATE INDEX IF NOT EXISTS idx_opportunities_tags ON opportunities USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_opportunities_url_hash ON opportunities(url_hash);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_type ON opportunities(opportunity_type);

CREATE TABLE IF NOT EXISTS company_hiring_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    company_slug TEXT,
    category TEXT,
    window_type TEXT,
    event_date DATE NOT NULL,
    year INTEGER,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,
    source_url TEXT,
    notes TEXT,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_company_hiring_windows_name ON company_hiring_windows(company_name);
CREATE INDEX IF NOT EXISTS idx_company_hiring_windows_date ON company_hiring_windows(event_date);

-- ── Scraping State (cursor persistence for incremental scrapers) ─────────
CREATE TABLE IF NOT EXISTS scraping_state (
    source TEXT PRIMARY KEY,
    state_data TEXT DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Source Health Tracking ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_health (
    source TEXT PRIMARY KEY,
    last_successful_scrape TIMESTAMPTZ DEFAULT NULL,
    jobs_added INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'unknown'
);

-- ── User Profile (single-tenant) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    education_year INTEGER DEFAULT NULL,
    degree TEXT DEFAULT '',
    skills TEXT DEFAULT '',
    preferred_roles TEXT DEFAULT '',
    remote_preference BOOLEAN DEFAULT FALSE,
    expected_salary TEXT DEFAULT '',
    is_fresher_seeking BOOLEAN DEFAULT FALSE,
    is_internship_seeking BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
