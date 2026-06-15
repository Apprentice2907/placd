"""
Placd — MinHash LSH Job Deduplicator

Fuzzy deduplication across sources to prevent identical jobs (e.g. from Greenhouse and LinkedIn)
from appearing multiple times.

Utilizes datasketch MinHashLSH for fast approximate Jaccard similarity.
"""
import re
import pickle
import logging
from typing import List, Dict, Any, Optional

from datasketch import MinHash, MinHashLSH
from sqlalchemy import text
from db.connection import AsyncSessionLocal
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

# Basic async Redis client setup based on a REDIS_URL or default
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
redis_client = redis.from_url(REDIS_URL)

class JobDeduplicator:
    def __init__(self, threshold: float = 0.85, num_perm: int = 128):
        self.threshold = threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self.is_loaded = False

    def text_signature(self, job: Dict[str, Any]) -> str:
        """
        Canonical string for comparison: f"{title.lower()} {company.lower()} {location.lower()}"
        Strip punctuation, normalize whitespace
        """
        title = job.get("title", "") or ""
        company = job.get("company_name", job.get("company", "")) or ""
        location = job.get("location", "") or ""

        raw_str = f"{title.lower()} {company.lower()} {location.lower()}"
        # Remove punctuation
        no_punct = re.sub(r'[^\w\s]', ' ', raw_str)
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', no_punct).strip()
        return normalized

    def compute_minhash(self, text_sig: str) -> MinHash:
        """num_perm=128, shingle size=3 (character trigrams)"""
        m = MinHash(num_perm=self.num_perm)
        # Create character trigrams
        for i in range(len(text_sig) - 2):
            shingle = text_sig[i:i+3]
            m.update(shingle.encode('utf8'))
        return m

    async def is_duplicate(self, job: Dict[str, Any], threshold: float = 0.85) -> Optional[str]:
        """
        Query LSH index. Return the ID of the duplicate job if found, else None.
        """
        sig = self.text_signature(job)
        if not sig:
            return None
            
        m = self.compute_minhash(sig)
        result = self.lsh.query(m)
        
        if result:
            # Return the first match as the duplicate reference
            return result[0]
        return None

    def add_to_index(self, job_id: str, job: Dict[str, Any]):
        """Add job to in-memory LSH index."""
        sig = self.text_signature(job)
        if not sig:
            return
        m = self.compute_minhash(sig)
        # If it's already in the LSH index, datasketch might raise ValueError for duplicate keys.
        # We can handle or ignore it.
        try:
            self.lsh.insert(job_id, m)
        except ValueError:
            pass

    async def load_index_from_db(self):
        """
        On startup: load last 30 days of active jobs into LSH index.
        Use batches of 1000 to avoid memory spike.
        Also tries Redis backup first to speed up boot.
        """
        if self.is_loaded:
            return

        # 1. Try to load from Redis
        try:
            redis_data = await redis_client.get("lsh_index:snapshot")
            if redis_data:
                self.lsh = pickle.loads(redis_data)
                self.is_loaded = True
                logger.info("Loaded LSH index from Redis snapshot.")
                return
        except Exception as e:
            logger.warning(f"Failed to load LSH from Redis: {e}")

        # 2. Fallback: rebuild from DB
        logger.info("Rebuilding LSH index from PostgreSQL (last 30 days)...")
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        loaded_count = 0

        try:
            async with AsyncSessionLocal() as session:
                # We use an offset/limit pagination approach
                batch_size = 1000
                offset = 0

                while True:
                    res = await session.execute(
                        text("""
                            SELECT j.id, j.title, j.location, c.name as company_name 
                            FROM jobs j
                            LEFT JOIN companies c ON j.company_id = c.id
                            WHERE j.status = 'active' 
                              AND j.created_at >= NOW() - INTERVAL '30 days'
                            ORDER BY j.created_at DESC
                            LIMIT :limit OFFSET :offset
                        """),
                        {"limit": batch_size, "offset": offset}
                    )
                    rows = res.fetchall()
                    if not rows:
                        break

                    for row in rows:
                        job_dict = {
                            "title": row.title,
                            "location": row.location,
                            "company_name": row.company_name
                        }
                        self.add_to_index(str(row.id), job_dict)
                        loaded_count += 1

                    offset += batch_size
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL to rebuild LSH index: {e}")
            # We still set is_loaded=True so we don't keep retrying and failing if DB is genuinely down
            self.is_loaded = True
            return

        self.is_loaded = True
        logger.info(f"Rebuilt LSH index with {loaded_count} jobs from database.")
        
        # Save the rebuilt index to Redis
        await self.backup_to_redis()

    async def backup_to_redis(self):
        """Serialize index to Redis every 10 minutes (TTL: 3600)"""
        try:
            serialized = pickle.dumps(self.lsh)
            await redis_client.setex("lsh_index:snapshot", 3600, serialized)
        except Exception as e:
            logger.warning(f"Failed to backup LSH index to Redis: {e}")

    async def bulk_deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates WITHIN the current batch only.
        
        We do NOT check against the DB/LSH index because existing jobs re-scraped
        across runs are correctly handled by the url_hash ON CONFLICT UPSERT in
        database.py. Checking against the DB index would falsely mark all
        re-scraped jobs as 'duplicate', hiding them from search results.
        
        This method only removes genuine same-batch duplicates (e.g. if two
        different keyword searches return the same job in one run).
        """
        unique_jobs = []
        
        # Track signatures seen within this batch (by exact url_hash first, then fuzzy)
        seen_urls: set = set()
        batch_signatures: dict = {}

        for job in jobs:
            # Primary dedup: exact URL match (cheapest check first)
            url = job.get("apply_url") or job.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            # Secondary dedup: fuzzy title+company+location within batch
            sig = self.text_signature(job)
            if sig and sig in batch_signatures:
                # Only skip if it's from a different URL (true fuzzy dup)
                continue
            if sig:
                batch_signatures[sig] = url or str(id(job))

            unique_jobs.append(job)

        logger.info(f"Batch dedup: {len(jobs)} in -> {len(unique_jobs)} unique ({len(jobs) - len(unique_jobs)} removed)")
        return unique_jobs

# Global instance
deduplicator = JobDeduplicator()
