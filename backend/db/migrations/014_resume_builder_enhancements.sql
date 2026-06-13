CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    portfolio_url TEXT,
    professional_summary TEXT,
    education JSONB,
    experiences JSONB,
    projects JSONB,
    skills JSONB,
    certifications JSONB,
    achievements JSONB,
    languages JSONB,
    raw_resume_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create generated_resumes table
CREATE TABLE IF NOT EXISTS generated_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    job_url TEXT,
    job_title TEXT,
    company_name TEXT,
    ats_score_before INTEGER,
    ats_score_after INTEGER,
    keywords_missing TEXT[],
    keywords_added TEXT[],
    recommendations TEXT[],
    docx_url TEXT,
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster history lookups
CREATE INDEX IF NOT EXISTS idx_generated_resumes_session ON generated_resumes (session_id);
