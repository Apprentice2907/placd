import os
import json
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

import structlog
from celery import shared_task
from sqlalchemy import text
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

import google.generativeai as genai
from google.generativeai.types import generation_types

# Reuse DB connection and Redis
from db.connection import AsyncSessionLocal
from utils.redis import redis_client
from utils.async_utils import run_async

logger = structlog.get_logger(__name__)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

DAILY_TOKEN_BUDGET = 1_000_000

ENRICHMENT_PROMPT = """
You are a job data extraction API. Extract structured data from these job postings.
Respond ONLY with a valid JSON array of objects. No markdown, no explanation, no preamble.

Job Postings:
{job_postings_json}

For each job posting, extract and return this exact JSON structure in an array (preserve the exact order of the input):
[
  {{
    "job_id": "...",              // Use the id provided in the input
    "skills_required": [],        // list of specific technical skills mentioned (max 20)
    "skills_preferred": [],       // nice-to-have skills (max 10)
    "experience_min_years": null, // integer or null
    "experience_max_years": null, // integer or null
    "seniority_level": null,      // "intern"|"junior"|"mid"|"senior"|"staff"|"lead"|"manager"|"director"|null
    "job_function": null,         // "engineering"|"data"|"product"|"design"|"devops"|"mobile"|"security"|"ml"|"other"
    "tech_stack": [],             // primary technologies/frameworks used
    "visa_sponsorship": null,     // true|false|null (null = not mentioned)
    "equity_offered": null,       // true|false|null
    "remote_type": null,          // "fully_remote"|"hybrid"|"onsite"|null
    "salary_mentioned": false,    // boolean
    "languages_required": [],     // human languages if mentioned (e.g. ["English", "Hindi"])
    "role_summary": ""            // 2 sentence max summary of the role
  }}
]
"""

async def track_tokens_used(tokens: int):
    """Track daily tokens in Redis."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"daily_tokens:{today}"
    
    try:
        await redis_client.incrby(key, tokens)
        await redis_client.expire(key, 172800)
    except Exception as e:
        logger.warning("token_tracking_failed", error=str(e))

async def get_daily_tokens_used() -> int:
    """Get the token usage for today."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"daily_tokens:{today}"
    try:
        val = await redis_client.get(key)
        return int(val) if val else 0
    except Exception:
        return 0

def _parse_gemini_json(response_text: str) -> list:
    """Extract JSON from Gemini response handling markdown blocks."""
    text = response_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    return json.loads(text)

def should_retry_gemini(exception: Exception) -> bool:
    """Retry on rate limits (429) or Internal server errors (500, 503)."""
    if isinstance(exception, generation_types.StopCandidateException):
        return False
    error_str = str(exception)
    if "429" in error_str or "503" in error_str or "500" in error_str or "Quota" in error_str:
        return True
    return False

def extract_jobs_batch(jobs: List[Dict[str, Any]]) -> tuple[List[Dict], float]:
    """Extracts data for up to 10 jobs using Gemini Flash Lite. Returns list of parsed dicts and cost."""
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    
    # Prepare input payload
    job_inputs = []
    for job in jobs:
        desc = (job.get("description") or "")[:3000]
        job_inputs.append({
            "id": job.get("id"),
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("location", ""),
            "description": desc
        })
        
    prompt = ENRICHMENT_PROMPT.format(job_postings_json=json.dumps(job_inputs, indent=2))
    total_cost = 0.0
    
    for attempt in range(2):
        try:
            response = model.generate_content(
                [{"role": "user", "parts": [prompt]}],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            
            usage = response.usage_metadata
            if usage:
                run_async(track_tokens_used(usage.total_token_count))
                # Gemini 2.0 Flash Lite cost estimate
                total_cost = (usage.prompt_token_count / 1_000_000) * 0.075 + (usage.candidates_token_count / 1_000_000) * 0.30
            
            try:
                parsed_data = _parse_gemini_json(response.text)
                if isinstance(parsed_data, list):
                    return parsed_data, total_cost
            except json.JSONDecodeError as e:
                if attempt == 0:
                    logger.warning("gemini_json_decode_error, retrying", error=str(e))
                    prompt = "Your previous response was not valid JSON. Return ONLY the JSON array, nothing else."
                    continue
                else:
                    logger.error("gemini_json_decode_error_final", error=str(e))
                    return [], total_cost
                    
        except Exception as e:
            if should_retry_gemini(e):
                raise e
            logger.error("extract_jobs_batch_failed", error=str(e))
            return [], total_cost
            
    return [], total_cost

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def compute_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Compute embeddings using models/embedding-001."""
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=texts,
            task_type="retrieval_document"
        )
        embeddings = result.get('embedding', [])
        # If a single string was passed accidentally, wrap it
        if embeddings and not isinstance(embeddings[0], list):
            embeddings = [embeddings]
        return embeddings
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("compute_embedding_failed", error=str(e))
        return [[] for _ in texts]

async def _batch_enrich_async():
    logger.info("starting_batch_enrich")
    
    # Check token budget
    tokens_used = await get_daily_tokens_used()
    if tokens_used > DAILY_TOKEN_BUDGET:
        logger.warning("token_budget_exceeded", used=tokens_used, limit=DAILY_TOKEN_BUDGET)
        return
        
    async with AsyncSessionLocal() as session:
        # Fetch 50 jobs at a time to maximize Celery beat efficiency
        result = await session.execute(
            text("""
                SELECT jobs.id, jobs.title, jobs.location, jobs.description, companies.name AS company_name 
                FROM jobs 
                LEFT JOIN companies ON jobs.company_id = companies.id
                WHERE jobs.status = 'active'
                  AND (jobs.skills_raw IS NULL OR jobs.enriched_at < NOW() - INTERVAL '7 days')
                ORDER BY jobs.created_at DESC
                LIMIT 50
            """)
        )
        jobs = result.fetchall()
        
        if not jobs:
            logger.info("no_jobs_to_enrich")
            return
            
        logger.info("enriching_jobs_total", count=len(jobs))
        
        # Process in chunks of 10
        chunk_size = 10
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i:i + chunk_size]
            
            job_dicts = []
            for r in chunk:
                job_dicts.append({
                    "id": str(r.id),
                    "title": r.title or "",
                    "company_name": r.company_name or "",
                    "location": r.location or "",
                    "description": r.description or ""
                })
                
            # 1. Extract structural JSON using Gemini
            parsed_results, chunk_cost = extract_jobs_batch(job_dicts)
            
            # 2. Compute Embeddings
            embed_texts = [f"{j['title']} at {j['company_name']}. {j['description'][:500]}" for j in job_dicts]
            embeddings = compute_embeddings_batch(embed_texts)
            
            cost_per_job = chunk_cost / len(chunk) if chunk else 0.0
            
            # Update DB
            for idx, job in enumerate(job_dicts):
                job_id = job["id"]
                
                # Find corresponding parsed result by job_id
                parsed = next((pr for pr in parsed_results if pr.get("job_id") == job_id), None)
                
                embedding = embeddings[idx] if idx < len(embeddings) else []
                embedding_str = f"[{','.join(map(str, embedding))}]" if embedding else None
                
                remote_type = parsed.get("remote_type") if parsed else None
                is_remote = True if remote_type == "fully_remote" else None
                
                experience_level = parsed.get("seniority_level", "") if parsed else ""
                
                await session.execute(
                    text("""
                        UPDATE jobs 
                        SET skills_raw = CAST(:skills_raw AS JSONB),
                            enriched_at = NOW(),
                            enrichment_cost_usd = :cost,
                            is_remote = COALESCE(:is_remote, is_remote),
                            experience_level = COALESCE(NULLIF(:experience_level, ''), experience_level),
                            description_embedding = COALESCE(CAST(:embedding AS vector), description_embedding)
                        WHERE id = :id
                    """),
                    {
                        "id": job_id,
                        "skills_raw": json.dumps(parsed) if parsed else None,
                        "cost": cost_per_job,
                        "is_remote": is_remote,
                        "experience_level": experience_level,
                        "embedding": embedding_str
                    }
                )
                
            await session.commit()
            logger.info("batch_enrich_chunk_complete", chunk_size=len(chunk), cost=chunk_cost)

@shared_task(name="batch_enrich_task")
def batch_enrich_task():
    """Celery beat task to periodically enrich raw jobs."""
    run_async(_batch_enrich_async())
