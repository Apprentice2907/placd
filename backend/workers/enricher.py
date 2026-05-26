import os
import json
import re
import asyncio
from typing import List, Optional
from datetime import datetime

import structlog
from pydantic import BaseModel, Field
from celery import shared_task
from sqlalchemy import text
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

import google.generativeai as genai
from google.generativeai.types import generation_types

# Reuse DB connection and Redis
from db.connection import AsyncSessionLocal
from scrapers.ats.base import redis_client, JobData

logger = structlog.get_logger(__name__)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

DAILY_TOKEN_BUDGET = 1_000_000

class EnrichmentResult(BaseModel):
    job_type: str = Field(default="")
    experience_level: str = Field(default="")
    is_remote: bool = Field(default=False)
    categories: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    salary_mentioned: bool = Field(default=False)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None


async def track_tokens_used(tokens: int):
    """Track daily tokens in Redis."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"daily_tokens:{today}"
    
    # Increment and set expiry for 48 hours to be safe
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

def _parse_gemini_json(response_text: str) -> dict:
    """Extract JSON from Gemini response handling markdown blocks."""
    text = response_text.strip()
    if text.startswith("```"):
        # Extract between markdown ticks
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("gemini_json_decode_error", text=response_text, error=str(e))
        return {}

def should_retry_gemini(exception: Exception) -> bool:
    """Retry on rate limits (429) or Internal server errors (500, 503)."""
    if isinstance(exception, generation_types.StopCandidateException):
        return False
    # If it's an API error, it might be embedded in the Exception string
    error_str = str(exception)
    if "429" in error_str or "503" in error_str or "500" in error_str or "Quota" in error_str:
        return True
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def classify_job(job: JobData) -> EnrichmentResult:
    """Classify a job using Gemini 2.5 Flash."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    system_prompt = "You are a job classification engine. Respond ONLY with valid JSON. No markdown, no explanation."
    
    user_prompt = f"""Classify this job posting:
Title: {job.title}
Company: {job.company_name}
Location: {job.location}
Description (first 500 chars): {job.description[:500]}

Return JSON:
{{
"job_type": "fulltime|internship|contract|research|parttime",
"experience_level": "entry|mid|senior|staff|lead|intern",
"is_remote": true|false,
"categories": ["array", "of", "applicable", "tags"],
"skills": ["python", "react", "sql", ...],
"salary_mentioned": true|false,
"salary_min": null_or_integer,
"salary_max": null_or_integer,
"salary_currency": "USD|INR|GBP|EUR|null"
}}

Category options (pick all that apply):
faang, big_tech, startup, unicorn, hft, quant, ai_lab, research, new_grad, remote_first, india, internship, contract, fintech, healthcare, edtech, deeptech
"""

    try:
        # Since the Google AI python SDK can be synchronous, we run it normally.
        response = model.generate_content(
            [{"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        # Track tokens
        usage = response.usage_metadata
        if usage:
            # Using asyncio.run inside synchronous wrapper is dangerous if event loop is running.
            # But celery tasks run synchronously, so we can dispatch the tracking to the background if needed,
            # or just call it directly if we ensure we handle the event loop.
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(track_tokens_used(usage.total_token_count))
                else:
                    loop.run_until_complete(track_tokens_used(usage.total_token_count))
            except RuntimeError:
                asyncio.run(track_tokens_used(usage.total_token_count))
        
        parsed_data = _parse_gemini_json(response.text)
        return EnrichmentResult(**parsed_data)
        
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("classify_job_failed", error=str(e), job_id=job.external_id)
        return EnrichmentResult()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def generate_resume_keywords(job: JobData) -> List[str]:
    """Extract ATS keywords using Gemini 2.5 Flash."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    system_prompt = "Extract the 15 most important ATS keywords from this job description for resume optimization. Return ONLY a JSON array of strings. No explanation."
    user_prompt = f"{job.description[:2000]}"
    
    try:
        response = model.generate_content(
            [{"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        usage = response.usage_metadata
        if usage:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(track_tokens_used(usage.total_token_count))
                else:
                    loop.run_until_complete(track_tokens_used(usage.total_token_count))
            except RuntimeError:
                asyncio.run(track_tokens_used(usage.total_token_count))
                
        keywords = _parse_gemini_json(response.text)
        if isinstance(keywords, list):
            return keywords
        return []
        
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("generate_resume_keywords_failed", error=str(e), job_id=job.external_id)
        return []

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def compute_embedding(text: str) -> List[float]:
    """Compute embeddings using text-embedding-004."""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        # text-embedding-004 returns 768 dimensions by default.
        # It allows output_dimensionality parameter for lower dimensions, but not higher.
        # If the DB expects 1536 (OpenAI size), we might have a schema mismatch.
        # We will return the embedding as provided by the model.
        embedding = result.get('embedding', [])
        return embedding
    except Exception as e:
        if should_retry_gemini(e):
            raise e
        logger.error("compute_embedding_failed", error=str(e))
        return []

async def _enrich_job_async(job_id: str):
    logger.info("starting_enrich_job", job_id=job_id)
    
    async with AsyncSessionLocal() as session:
        # Load job
        result = await session.execute(
            text("SELECT * FROM jobs WHERE id = :id"),
            {"id": job_id}
        )
        row = result.fetchone()
        if not row:
            logger.error("job_not_found", job_id=job_id)
            return
            
        # Map DB row to JobData
        job = JobData(
            external_id=row.external_id or str(row.id),
            title=row.title or "",
            description=row.description or "",
            apply_url=row.apply_url or "",
            source=row.source or "",
            job_type=row.job_type or "",
            location=row.location or "",
            is_remote=row.is_remote or False,
            company_slug="", # Not strictly needed for enrichment logic below
            company_name=row.company_name or "", # Assuming company_name exists, else use slug
            raw_data={},
            scraped_at=datetime.utcnow()
        )
        
        # 1. Classify
        classification = classify_job(job)
        
        # 2. Keywords
        keywords = generate_resume_keywords(job)
        
        # 3. Embedding
        embed_text = f"{job.title} at {job.company_name}. {job.description[:500]}"
        embedding = compute_embedding(embed_text)
        
        # Update jobs table
        # Format lists for PostgreSQL arrays/JSON
        categories_json = json.dumps(classification.categories)
        skills_json = json.dumps(classification.skills)
        # For pgvector, string representation: '[0.1, 0.2, ...]'
        embedding_str = f"[{','.join(map(str, embedding))}]" if embedding else None
        
        await session.execute(
            text("""
                UPDATE jobs 
                SET job_type = COALESCE(NULLIF(:job_type, ''), job_type),
                    experience_level = :experience_level,
                    is_remote = :is_remote,
                    tags = :tags::jsonb,
                    skills = :skills::jsonb,
                    description_embedding = :embedding::vector,
                    is_enriched = 1,
                    enrichment_timestamp = NOW()
                WHERE id = :id
            """),
            {
                "id": job_id,
                "job_type": classification.job_type,
                "experience_level": classification.experience_level,
                "is_remote": classification.is_remote,
                "tags": categories_json,
                "skills": skills_json,
                "embedding": embedding_str
            }
        )
        
        # Insert keywords
        if keywords:
            # Delete old keywords just in case
            await session.execute(text("DELETE FROM job_keywords WHERE job_id = :id"), {"id": job_id})
            
            # Simple weighting: first is 1.0, decreasing
            for i, kw in enumerate(keywords):
                weight = max(0.1, 1.0 - (i * 0.05))
                await session.execute(
                    text("""
                        INSERT INTO job_keywords (job_id, keyword, weight)
                        VALUES (:job_id, :keyword, :weight)
                    """),
                    {"job_id": job_id, "keyword": kw, "weight": weight}
                )
                
        await session.commit()
        logger.info("enrich_job_complete", job_id=job_id)

@shared_task(name="enrich_job_task")
def enrich_job_task(job_id: str):
    """Celery task to run enrichment pipeline on a single job."""
    asyncio.run(_enrich_job_async(job_id))

async def _batch_enrich_async():
    logger.info("starting_batch_enrich")
    
    # Check token budget
    tokens_used = await get_daily_tokens_used()
    if tokens_used > DAILY_TOKEN_BUDGET:
        logger.warning("token_budget_exceeded", used=tokens_used, limit=DAILY_TOKEN_BUDGET)
        return
        
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id FROM jobs 
                WHERE tags IS NULL 
                  AND created_at > NOW() - INTERVAL '1 day' 
                LIMIT 200
            """)
        )
        jobs = result.fetchall()
        
    if not jobs:
        logger.info("no_jobs_to_enrich")
        return
        
    logger.info("dispatching_enrich_tasks", count=len(jobs))
    for index, row in enumerate(jobs):
        # Stagger by 0.5 seconds
        delay = index * 0.5
        enrich_job_task.apply_async(args=[str(row.id)], countdown=delay)

@shared_task(name="batch_enrich_task")
def batch_enrich_task():
    """Celery beat task to periodically enrich raw jobs."""
    asyncio.run(_batch_enrich_async())
