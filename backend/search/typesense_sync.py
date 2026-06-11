import os
import structlog
import typesense
import asyncio
from datetime import datetime
from typing import List, Dict, Any

logger = structlog.get_logger(__name__)

TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "plcd_local_ts_key")
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_ENABLED = os.getenv("TYPESENSE_ENABLED", "true").lower() == "true"


TYPESENSE_SCHEMA = {
    "name": "jobs",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "title", "type": "string"},
        {"name": "title_normalized", "type": "string"},
        {"name": "company", "type": "string"},
        {"name": "location_city", "type": "string", "optional": True},
        {"name": "location_country", "type": "string", "optional": True},
        {"name": "is_remote", "type": "bool"},
        {"name": "is_student_eligible", "type": "bool", "facet": True, "optional": True},
        {"name": "seniority_level", "type": "string", "optional": True, "facet": True},
        {"name": "job_function", "type": "string", "optional": True, "facet": True},
        {"name": "skills_required", "type": "string[]", "facet": True, "optional": True},
        {"name": "salary_min_usd", "type": "int32", "optional": True},
        {"name": "salary_max_usd", "type": "int32", "optional": True},
        {"name": "source_platform", "type": "string", "facet": True, "optional": True},
        {"name": "created_at", "type": "int64"},  # unix timestamp
        {"name": "status", "type": "string", "facet": True},
        {"name": "role_summary", "type": "string", "optional": True},
        {"name": "freshness_score", "type": "float"},
    ],
    "default_sorting_field": "freshness_score"
}

def get_client() -> typesense.Client:
    return typesense.Client({
        'nodes': [{
            'host': TYPESENSE_HOST,
            'port': TYPESENSE_PORT,
            'protocol': TYPESENSE_PROTOCOL
        }],
        'api_key': TYPESENSE_API_KEY,
        'connection_timeout_seconds': 5
    })

def _ensure_collection_exists(client: typesense.Client):
    """Ensure the jobs collection exists in Typesense."""
    try:
        client.collections['jobs'].retrieve()
    except typesense.exceptions.ObjectNotFound:
        logger.info("creating_typesense_collection", schema=TYPESENSE_SCHEMA['name'])
        client.collections.create(TYPESENSE_SCHEMA)

class TypesenseSync:
    def __init__(self):
        self.client = get_client()
        self._initialized = False

    def _init_once(self):
        if not self._initialized:
            _ensure_collection_exists(self.client)
            self._initialized = True

    def _map_job_to_ts(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a DB job dictionary into Typesense schema format."""
        skills = []
        role_summary = ""
        job_function = ""
        seniority = ""
        
        # Handle skills_raw JSON string or dict
        skills_raw = job.get('skills_raw')
        if skills_raw:
            import json
            if isinstance(skills_raw, str):
                try:
                    parsed = json.loads(skills_raw)
                except Exception:
                    parsed = {}
            else:
                parsed = skills_raw
                
            skills = parsed.get("skills_required", [])
            role_summary = parsed.get("role_summary", "")
            job_function = parsed.get("job_function", "")
            seniority = parsed.get("seniority_level", "")

        created_at = job.get('created_at')
        if isinstance(created_at, datetime):
            created_at_ts = int(created_at.timestamp())
        elif isinstance(created_at, str):
            try:
                created_at_ts = int(datetime.fromisoformat(created_at).timestamp())
            except Exception:
                created_at_ts = int(datetime.utcnow().timestamp())
        else:
            created_at_ts = int(datetime.utcnow().timestamp())

        # Fallback fields
        if not seniority:
            seniority = job.get("experience_level", "")
            
        location_city = ""
        location = job.get("location", "")
        if location:
            location_city = location.split(",")[0].strip()

        ts_doc = {
            "id": str(job.get("id")),
            "title": job.get("title", ""),
            "title_normalized": job.get("title", "").lower(),
            "company": job.get("company_name", job.get("company", "")),
            "is_remote": bool(job.get("is_remote", False)),
            "is_student_eligible": bool(job.get("is_student_eligible", False)),
            "created_at": created_at_ts,
            "status": job.get("status", "active"),
        }
        
        if location_city: ts_doc["location_city"] = location_city
        if seniority: ts_doc["seniority_level"] = seniority
        if job_function: ts_doc["job_function"] = job_function
        if skills: ts_doc["skills_required"] = skills
        if role_summary: ts_doc["role_summary"] = role_summary
        
        salary_min = job.get("salary_min")
        if salary_min is not None: ts_doc["salary_min_usd"] = int(salary_min)
        salary_max = job.get("salary_max")
        if salary_max is not None: ts_doc["salary_max_usd"] = int(salary_max)
        
        freshness_score = job.get("freshness_score")
        ts_doc["freshness_score"] = float(freshness_score) if freshness_score is not None else 1.0
        
        source_platform = job.get("source_platform") or job.get("source")
        if source_platform: ts_doc["source_platform"] = source_platform

        return ts_doc

    async def upsert_job(self, job: Dict[str, Any]):
        """Upsert a single job into Typesense."""
        if not TYPESENSE_ENABLED:
            return

        def _do_upsert():
            self._init_once()
            ts_doc = self._map_job_to_ts(job)
            self.client.collections['jobs'].documents.upsert(ts_doc)
            
        try:
            await asyncio.to_thread(_do_upsert)
        except Exception as e:
            logger.error("typesense_upsert_failed", error=str(e), job_id=job.get('id'))

    async def upsert_batch(self, jobs: List[Dict[str, Any]], batch_size=100):
        """Upsert a list of jobs in batches."""
        if not TYPESENSE_ENABLED or not jobs:
            return
            
        def _do_upsert_batch():
            self._init_once()
            docs = [self._map_job_to_ts(j) for j in jobs if j.get('id')]
            if not docs:
                return
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i+batch_size]
                self.client.collections['jobs'].documents.import_(batch, {'action': 'upsert'})
                
        try:
            await asyncio.to_thread(_do_upsert_batch)
        except Exception as e:
            logger.error("typesense_upsert_batch_failed", error=str(e), count=len(jobs))

    async def delete_job(self, job_id: str):
        """Delete a job from Typesense."""
        if not TYPESENSE_ENABLED:
            return

        def _do_delete():
            self._init_once()
            self.client.collections['jobs'].documents[job_id].delete()
            
        try:
            await asyncio.to_thread(_do_delete)
        except typesense.exceptions.ObjectNotFound:
            pass # Already deleted or not present
        except Exception as e:
            logger.error("typesense_delete_failed", error=str(e), job_id=job_id)

    async def search(self, query: str, filters: Dict[str, Any], page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Perform a search query."""
        if not TYPESENSE_ENABLED:
            return {"hits": [], "found": 0, "page": page}

        def _do_search():
            self._init_once()
            search_params = {
                'q': query if query else '*',
                'query_by': 'title,company,skills_required',
                'page': page,
                'per_page': per_page,
                'facet_by': 'seniority_level,job_function,skills_required,source_platform,status',
            }
            
            filter_by = []
            if filters.get('is_remote') is not None:
                filter_by.append(f"is_remote:={str(filters['is_remote']).lower()}")
            if filters.get('seniority'):
                filter_by.append(f"seniority_level:={filters['seniority']}")
            if filters.get('function'):
                filter_by.append(f"job_function:={filters['function']}")
            if filters.get('status'):
                filter_by.append(f"status:={filters['status']}")
            
            if filter_by:
                search_params['filter_by'] = ' && '.join(filter_by)
                
            return self.client.collections['jobs'].documents.search(search_params)
            
        return await asyncio.to_thread(_do_search)

    async def full_reindex(self):
        """Backfill all active jobs from PostgreSQL to Typesense."""
        if not TYPESENSE_ENABLED:
            logger.info("typesense_disabled_skipping_reindex")
            return

        from db.connection import AsyncSessionLocal
        from sqlalchemy import text
        
        logger.info("starting_full_reindex")
        
        async with AsyncSessionLocal() as session:
            # We use cursor/limit-offset to fetch all active jobs
            limit = 1000
            offset = 0
            while True:
                res = await session.execute(
                    text("""
                        SELECT j.*, c.name as company_name 
                        FROM jobs j
                        LEFT JOIN companies c ON j.company_id = c.id
                        WHERE j.status = 'active'
                        ORDER BY j.id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"limit": limit, "offset": offset}
                )
                rows = res.fetchall()
                if not rows:
                    break
                    
                jobs = [dict(r._mapping) for r in rows]
                await self.upsert_batch(jobs, batch_size=200)
                offset += limit
                
        logger.info("full_reindex_complete")

# Singleton instance
typesense_sync = TypesenseSync()
