-- Migration 012: Add student eligible column
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_student_eligible BOOLEAN DEFAULT FALSE;

UPDATE jobs SET is_student_eligible = TRUE 
WHERE (
  job_type = 'internship'
  OR title ILIKE ANY(ARRAY['%intern%','%fresher%','%trainee%','%new grad%','%campus%','%apprentice%','%graduate program%'])
  OR description ILIKE ANY(ARRAY['%pre-final year%','%penultimate year%','%pursuing%','%3rd year%','%third year%','%2025 batch%','%2026 batch%','%2027 batch%','%currently enrolled%','%undergraduate%','%0-1 year%','%0 to 1%','%entry level%'])
)
AND title NOT ILIKE ANY(ARRAY['%senior %','%staff %','%principal %','%director%','%vp of%','% lead %']);

CREATE INDEX IF NOT EXISTS idx_jobs_student_eligible ON jobs(is_student_eligible) WHERE is_student_eligible = TRUE;
