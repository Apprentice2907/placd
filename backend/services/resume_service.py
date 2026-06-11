import os
import re
import json
import asyncio
from typing import Dict, List, Any
import google.generativeai as genai
from utils.json_parser import clean_and_parse_json

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

def slugify(text: str) -> str:
    if not text:
        return "unknown"
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

def flatten_bullets(profile: dict) -> list:
    items = []
    for exp in profile.get("experience", []):
        items.append({
            "id": exp.get("id"),
            "type": "experience",
            "company": exp.get("company"),
            "role": exp.get("role"),
            "raw_bullets": exp.get("bullets", [])
        })
    for proj in profile.get("projects", []):
        items.append({
            "id": proj.get("id"),
            "type": "project",
            "name": proj.get("name"),
            "stack": proj.get("stack", []),
            "raw_bullets": proj.get("bullets", [])
        })
    return items

async def research_company_role(company: str, role: str, jd_text: str, session_id: str = None, db_session = None) -> dict:
    cache_key = f"resume:research:{slugify(company)}:{slugify(role)}"
    
    redis_client = None
    try:
        from utils.redis import get_redis
        redis_client = get_redis()
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
    except Exception:
        pass
        
    if db_session:
        try:
            from sqlalchemy import text
            query = text("SELECT resume_research_cache FROM user_profile LIMIT 1")
            result = await db_session.execute(query)
            row = result.fetchone()
            if row and row[0]:
                cache_dict = row[0]
                if cache_key in cache_dict:
                    return cache_dict[cache_key]
        except Exception as e:
            print(f"Failed to read from db cache: {e}")

    prompt = f"""Target Company: {company}
Target Role: {role}

You are a resume research assistant. Search the web and answer the following about the target company and role.

Answer all four questions:
1. What technical keywords and skills appear most in job postings for this role at this company?
2. What do LinkedIn profiles of current employees in this role at this company emphasize?
3. Describe this company's engineering culture in 2-3 sentences.
4. What resume style does this company reward — quantified metrics, scope of impact, technical depth, domain knowledge?

Return ONLY valid JSON, no markdown, no preamble:
{{
  "top_keywords": ["keyword1", "keyword2"],
  "culture_signals": ["signal1", "signal2"],
  "emphasis_notes": "2-3 sentence string",
  "example_strong_bullets": ["bullet1", "bullet2"]
}}"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = await asyncio.to_thread(model.generate_content, prompt)
        result_json = clean_and_parse_json(response.text)
    except Exception as e:
        print(f"Gemini API failed: {e}")
        return {
            "top_keywords": [],
            "culture_signals": [],
            "emphasis_notes": "",
            "example_strong_bullets": []
        }

    try:
        if redis_client:
            redis_client.setex(cache_key, 7 * 24 * 3600, json.dumps(result_json))
    except Exception:
        pass
        
    if db_session:
        try:
            from sqlalchemy import text
            update_query = text(f"""
                UPDATE user_profile 
                SET resume_research_cache = jsonb_set(
                    resume_research_cache, 
                    '{{{cache_key}}}', 
                    :val::jsonb
                )
            """)
            await db_session.execute(update_query, {"val": json.dumps(result_json)})
            await db_session.commit()
        except Exception as e:
            print(f"Failed to write to db cache: {e}")

    return result_json

async def rewrite_resume(profile: dict, research: dict, jd_text: str) -> dict:
    flat_items = flatten_bullets(profile)
    
    prompt = f"""You are an ATS resume optimizer. Rewrite the user's resume bullets for the target role.

RULES — all are non-negotiable:
1. Never invent, change, or remove any number, metric, or statistic. Only append [ADD METRIC HERE] to bullets that contain zero numbers. If a bullet already contains any number, do not append this placeholder.
2. Prefer minimal edits. Change only what is necessary to improve ATS alignment. Do not restructure a bullet if the original structure is already strong.
3. Always retain every technical keyword the user mentioned — libraries, databases, frameworks, languages — even if absent from the JD. Tech stack preservation takes priority over length.
4. Each bullet must be a single sentence. Target 18–25 words. If retaining the full tech stack makes a bullet exceed 25 words, that is acceptable. Specificity is more valuable than keyword density. Prefer a concrete technical detail over a generic keyword.
5. Do not add responsibilities the user did not mention.
6. Write in past tense with strong action verbs. No personal pronouns.
7. Return the exact same IDs from the input array. Do not modify, shorten, or invent IDs.
8. The summary must reference the specific company name and role. Avoid generic phrases like 'passionate engineer' or 'results-driven developer'.
9. Reorder skills so that skills explicitly mentioned in the JD appear first, followed by related skills, followed by others. Return the same skills the user provided — do not add or remove any.

Target Job Description:
{jd_text}

Company emphasis notes:
{research.get('emphasis_notes', '')}

Top keywords to inject where natural:
{research.get('top_keywords', [])}

Items to rewrite (flat array):
{json.dumps(flat_items, indent=2)}

Return ONLY valid JSON:
{{
  "summary": "2-line professional summary tailored to this JD and company",
  "rewritten_bullets": [
    {{ "id": "exp_1", "bullets": ["bullet 1", "bullet 2"] }}
  ],
  "skills_reordered": ["skill1", "skill2"],
  "match_score": 87,
  "missing_keywords": ["keyword1", "keyword2"],
  "placeholders": ["exp_1: bullet 2 needs a metric for deployment impact"]
}}"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = await asyncio.to_thread(model.generate_content, prompt)
        result_json = clean_and_parse_json(response.text)
        
        # Coerce match_score to integer
        if "match_score" in result_json:
            try:
                result_json["match_score"] = int(result_json["match_score"])
            except (ValueError, TypeError):
                result_json["match_score"] = 0
                
        return result_json
    except Exception as e:
        print(f"Gemini API Rewrite failed: {e}")
        return {
            "summary": "Error generating summary.",
            "rewritten_bullets": [],
            "skills_reordered": [],
            "match_score": 0,
            "missing_keywords": [],
            "placeholders": []
        }
