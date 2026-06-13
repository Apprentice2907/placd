import os
import json
import re
import structlog
import anthropic
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = structlog.get_logger(__name__)

# Configure Anthropic
client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

RESUME_SELECTION_PROMPT = """
You are an expert ATS resume optimizer and career coach.

Given a candidate's complete profile and a specific job description,
your task is to select and tailor resume content for maximum ATS score
and relevance to this specific role.

CANDIDATE PROFILE:
{profile_json}

JOB DESCRIPTION:
Title: {job_title}
Company: {company_name}
Description: {job_description}

Your tasks:

1. PROJECT SELECTION
   From the candidate's projects, select the 2-3 BEST matches for this role.
   Criteria: tech stack overlap, domain relevance, impact demonstrated.

2. SKILLS SELECTION  
   From the candidate's skills, select and reorder for this role.
   Put skills explicitly mentioned in the JD first.

3. EXPERIENCE TAILORING
   For each experience entry, review the bullets.
   If a bullet can be reframed to emphasize a keyword from the JD, do so.
   Do NOT invent new achievements. Do NOT change numbers/metrics.

4. SUMMARY GENERATION
   Write a 2-3 sentence professional summary tailored to this specific
   role and company.

5. AI INSIGHTS & ATS METRICS
   Analyze the JD and candidate profile to provide:
   - ats_score_before: Int (0-100) raw match before tailoring.
   - ats_score_after: Int (0-100) estimated match after your tailoring.
   - keywords_present: Array of important JD keywords already in the profile.
   - keywords_missing: Array of important JD keywords completely missing.
   - keywords_added: Array of keywords you successfully wove into the tailored bullets.
   - recommendations: Array of 3-5 actionable tips (e.g. "Quantify your impact at X").
   - sections_to_emphasize: Array of sections that matter most.

Return ONLY valid JSON in this exact shape:
{{
  "selected_projects": ["project_name_1", "project_name_2"],
  "selected_skills": {{
    "languages": ["..."],
    "frameworks": ["..."],
    "databases": ["..."],
    "tools": ["..."]
  }},
  "tailored_experiences": [
    {{
      "company": "...",
      "bullets": ["rewritten bullet 1", "rewritten bullet 2"]
    }}
  ],
  "tailored_summary": "...",
  "ats_keywords": ["keyword1", "keyword2"],
  "match_score": 85,
  "ats_score_before": 60,
  "ats_score_after": 85,
  "keywords_present": ["..."],
  "keywords_missing": ["..."],
  "keywords_added": ["..."],
  "recommendations": ["..."],
  "sections_to_emphasize": ["..."]
}}
"""

COVER_LETTER_PROMPT = """
You are writing a professional cover letter for a job application.

CANDIDATE PROFILE: {profile_json}
JOB: {job_title} at {company_name}
JOB DESCRIPTION: {job_description}

Write a cover letter following these rules:
- 3 paragraphs: hook + why you fit + call to action
- Paragraph 1: specific to THIS company
- Paragraph 2: 2-3 specific examples from the candidate's experience
- Paragraph 3: confident close, not desperate
- Tone: professional but human
- Length: 250-320 words maximum
- Do NOT use phrases like "I am writing to apply for"

Start with: Dear Hiring Team at {company_name},
End with: Sincerely, {candidate_name}

Return only the letter text, no JSON wrapper.
"""

def _parse_json(response_text: str) -> dict:
    text = response_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
            
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("json_decode_error", text=response_text, error=str(e))
        return {}

def should_retry(exception: Exception) -> bool:
    error_str = str(exception).lower()
    if "429" in error_str or "503" in error_str or "500" in error_str or "rate limit" in error_str or "overloaded" in error_str:
        return True
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def generate_resume_content(profile_json: str, job_title: str, company_name: str, job_description: str) -> dict:
    prompt = RESUME_SELECTION_PROMPT.format(
        profile_json=profile_json,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description
    )
    
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # Assuming the response returns text content blocks
        text = response.content[0].text
        return _parse_json(text)
    except Exception as e:
        if should_retry(e):
            raise e
        logger.error("generate_resume_content_failed", error=str(e))
        return {}

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def generate_cover_letter_content(profile_json: str, candidate_name: str, job_title: str, company_name: str, job_description: str) -> str:
    prompt = COVER_LETTER_PROMPT.format(
        profile_json=profile_json,
        candidate_name=candidate_name,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description
    )
    
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        if should_retry(e):
            raise e
        logger.error("generate_cover_letter_content_failed", error=str(e))
        return ""
