import os
import hashlib
import time
import asyncio
from typing import List, Tuple, Any
from abc import ABC, abstractmethod
from datetime import datetime

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
import redis.asyncio as redis

try:
    from simhash import Simhash
except ImportError:
    # Graceful fallback if simhash is not yet installed
    Simhash = None

logger = structlog.get_logger(__name__)

# Basic async Redis client setup based on a REDIS_URL or default
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class JobData(BaseModel):
    external_id: str
    title: str
    description: str
    apply_url: str
    source: str
    job_type: str
    location: str
    is_remote: bool
    company_slug: str
    company_name: str
    raw_data: dict = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class BaseCrawler(ABC):
    
    @abstractmethod
    async def crawl_company(self, slug: str) -> List[JobData]:
        """Fetch all jobs for a given company slug and return parsed JobData models."""
        pass
        
    async def check_rate_limit(self, domain: str, max_requests: int = 10, window_seconds: int = 1) -> None:
        """
        Token bucket / sliding window rate limit using Redis.
        Ensures we don't exceed max_requests per window_seconds for a given domain.
        """
        key = f"rate_limit:{domain}"
        now = time.time()
        
        async with redis_client.pipeline(transaction=True) as pipe:
            # Remove timestamps older than our window
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            # Count how many requests are in the current window
            pipe.zcard(key)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Set expiry so we don't leak memory
            pipe.expire(key, window_seconds + 1)
            
            results = await pipe.execute()
            
        request_count = results[1]
        if request_count >= max_requests:
            # Sleep a bit to back off
            await asyncio.sleep(window_seconds)

    def _compute_hashes(self, job: JobData) -> Tuple[str, str]:
        """Compute URL hash (SHA256) and Content hash (Simhash or MD5)."""
        url_hash = hashlib.sha256(job.apply_url.encode("utf-8")).hexdigest()
        
        content_str = f"{job.title}|{job.company_name}|{job.location}"
        if Simhash:
            # Simhash library returns a 64-bit integer, we convert it to hex string
            content_hash = hex(Simhash(content_str).value)[2:].zfill(16)
        else:
            # Fallback to MD5 if simhash isn't installed
            content_hash = hashlib.md5(content_str.encode("utf-8")).hexdigest()
            
        return url_hash, content_hash
        
    async def save_jobs(self, jobs: List[JobData], db: Any, company_id: str = None) -> Tuple[int, int]:
        """
        Save parsed jobs to the database.
        Returns a tuple of (inserted_count, updated_count).
        """
        if not jobs:
            return 0, 0
            
        inserted_count = 0
        updated_count = 0
        
        query = text("""
            INSERT INTO jobs (
                company_id, external_id, title, description, apply_url, source, 
                job_type, location, is_remote, status, 
                url_hash, content_hash, last_verified_at
            ) VALUES (
                :company_id, :external_id, :title, :description, :apply_url, :source,
                :job_type, :location, :is_remote, 'active',
                :url_hash, :content_hash, :last_verified_at
            )
            ON CONFLICT (url_hash) DO UPDATE SET
                company_id = EXCLUDED.company_id,
                last_verified_at = EXCLUDED.last_verified_at,
                status = 'active'
            RETURNING (xmax = 0) AS inserted
        """)
        
        try:
            # Ensure we're managing the session properly depending on how db is passed
            session = db if hasattr(db, 'execute') else await db.__aenter__()
            
            for job in jobs:
                url_hash, content_hash = self._compute_hashes(job)
                
                result = await session.execute(query, {
                    "company_id": company_id,
                    "external_id": job.external_id,
                    "title": job.title,
                    "description": job.description,
                    "apply_url": job.apply_url,
                    "source": job.source,
                    "job_type": job.job_type,
                    "location": job.location,
                    "is_remote": job.is_remote,
                    "url_hash": url_hash,
                    "content_hash": content_hash,
                    "last_verified_at": job.scraped_at
                })
                
                row = result.fetchone()
                is_inserted = row.inserted if row else False
                
                if is_inserted:
                    inserted_count += 1
                    # TODO: If strictly new, create a sources record if your DB schema expects that
                else:
                    updated_count += 1
                    
            await session.commit()
            
            if not hasattr(db, 'execute'):
                await db.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error("error_saving_jobs", error=str(e))
            
        return inserted_count, updated_count
