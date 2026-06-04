import os
import json
import re
import structlog
import google.generativeai as genai
from google.generativeai.types import generation_types
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = structlog.get_logger(__name__)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

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
   Return selected project names in order of relevance.

2. SKILLS SELECTION  
   From the candidate's skills, select and reorder for this role.
   Put skills explicitly mentioned in the JD first.
   Remove skills completely unrelated to this role.
   Keep total skills under 20.

3. EXPERIENCE TAILORING
   For each experience entry, review the bullets.
   If a bullet can be reframed to emphasize a keyword from the JD, do so.
   Do NOT invent new achievements. Do NOT change numbers/metrics.
   Only reframe language while keeping facts identical.

4. SUMMARY GENERATION
   Write a 2-3 sentence professional summary tailored to this specific
   role and company. Include the job title they are applying for.
   Mention 2-3 of the candidate's strongest relevant qualifications.

5. ATS KEYWORDS
   List the top 15 keywords/phrases from the JD that an ATS would scan for.
   These should be naturally woven into the resume.

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
  "match_score": 85
}}

match_score is your estimate (0-100) of how well this candidate matches
this role based on their profile. Be honest, not optimistic.
"""

COVER_LETTER_PROMPT = """
You are writing a professional cover letter for a job application.

CANDIDATE PROFILE: {profile_json}
JOB: {job_title} at {company_name}
JOB DESCRIPTION: {job_description}

Write a cover letter following these rules:
- 3 paragraphs: hook + why you fit + call to action
- Paragraph 1: specific to THIS company (mention something real about
  the company from the JD — their mission, product, tech stack)
- Paragraph 2: 2-3 specific examples from the candidate's experience
  that match the role requirements. Use real numbers from their profile.
- Paragraph 3: confident close, not desperate
- Tone: professional but human — not corporate template language
- Length: 250-320 words maximum
- Do NOT use phrases like "I am writing to apply for" or 
  "I believe I am a strong candidate" — these are ATS-filtered clichés

Start with: Dear Hiring Team at {company_name},
End with: Sincerely, {candidate_name}

Return only the letter text, no JSON wrapper.
"""

def _parse_gemini_json(response_text: str) -> dict:
    text = response_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
            
    # Clean up trailing commas before closing braces/brackets
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("gemini_json_decode_error", text=response_text, error=str(e))
        return {}

def should_retry_gemini(exception: Exception) -> bool:
    if isinstance(exception, generation_types.StopCandidateException):
        return False
    error_str = str(exception)
    if "429" in error_str or "503" in error_str or "500" in error_str or "Quota" in error_str:
        return True
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate_resume_content(profile_json: str, job_title: str, company_name: str, job_description: str) -> dict:
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = RESUME_SELECTION_PROMPT.format(
        profile_json=profile_json,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description
    )
    
    try:
        response = model.generate_content(
            [{"role": "user", "parts": [prompt]}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        return _parse_gemini_json(response.text)
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("generate_resume_content_failed", error=str(e))
        return {}

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate_cover_letter_content(profile_json: str, candidate_name: str, job_title: str, company_name: str, job_description: str) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = COVER_LETTER_PROMPT.format(
        profile_json=profile_json,
        candidate_name=candidate_name,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description
    )
    
    try:
        response = model.generate_content([{"role": "user", "parts": [prompt]}])
        return response.text.strip()
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("generate_cover_letter_content_failed", error=str(e))
        return ""
