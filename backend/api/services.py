"""
Placd — API Services Layer (PostgreSQL)
All database queries use the async PostgreSQL engine.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Optional, List, Tuple

from sqlalchemy import text
from db.connection import AsyncSessionLocal


COMPANY_ALIASES = {
    'google': 'Google',
    'meta': 'Meta',
    'facebook': 'Meta',
    'msft': 'Microsoft',
    'microsoft': 'Microsoft',
    'amazon': 'Amazon',
    'aws': 'Amazon',
    'openai': 'OpenAI',
    'nvidia': 'NVIDIA',
    'apple': 'Apple',
    'netflix': 'Netflix'
}

def parse_search_query(query: str) -> dict:
    """Parses a search query for intents like company:, role:, skill:, collection:"""
    intents = {'company': None, 'role': None, 'skill': None, 'collection': None, 'text': ''}
    if not query:
        return intents
        
    parts = query.split()
    text_parts = []
    
    for part in parts:
        lower_part = part.lower()
        if lower_part.startswith('company:'):
            val = lower_part.split(':', 1)[1]
            intents['company'] = COMPANY_ALIASES.get(val, val)
        elif lower_part.startswith('role:'):
            intents['role'] = lower_part.split(':', 1)[1]
        elif lower_part.startswith('skill:'):
            intents['skill'] = lower_part.split(':', 1)[1]
        elif lower_part.startswith('collection:'):
            intents['collection'] = lower_part.split(':', 1)[1]
        else:
            text_parts.append(part)
            
    intents['text'] = ' '.join(text_parts)
    
    # Check if the remaining text is exactly a known company alias
    if intents['text'].lower() in COMPANY_ALIASES and not intents['company']:
        intents['company'] = COMPANY_ALIASES[intents['text'].lower()]
        intents['text'] = ''
        
    return intents


async def get_jobs_api(
    search: Optional[str] = None,
    remote: Optional[bool] = None,
    internship: Optional[bool] = None,
    fulltime: Optional[bool] = None,
    research: Optional[bool] = None,
    new_grad: Optional[bool] = None,
    experience: Optional[str] = None,
    hybrid: Optional[bool] = None,
    company_tier: Optional[str] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    min_score: float = 0.0,
    page: int = 1,
    limit: int = 50
) -> Tuple[int, List[dict]]:
    """Paginated job search with advanced filters — async PostgreSQL."""
    intents = parse_search_query(search) if search else {'company': None, 'role': None, 'skill': None, 'collection': None, 'text': ''}

    base_where = "jobs.status = 'active'"
    params: dict = {}
    param_idx = 0

    fts_conditions = []
    if intents['text']:
        fts_conditions.append(intents['text'])
    if intents['role']:
        fts_conditions.append(intents['role'])
    if intents['skill']:
        fts_conditions.append(intents['skill'])

    fts_query = " ".join(fts_conditions)

    if fts_query:
        base_where += " AND (to_tsvector('english', COALESCE(jobs.title, '') || ' ' || COALESCE(jobs.description, '')) @@ websearch_to_tsquery('english', :fts_q))"
        params["fts_q"] = fts_query

    if intents['company']:
        base_where += " AND jobs.source ILIKE :company_filter"
        params["company_filter"] = f"%{intents['company']}%"

    if remote:
        base_where += " AND jobs.is_remote = true"
    if internship:
        base_where += " AND jobs.job_type = 'internship'"
    if fulltime:
        base_where += " AND jobs.job_type = 'fulltime'"

    if city:
        base_where += " AND jobs.location ILIKE :city_filter"
        params["city_filter"] = f"%{city}%"
    if country:
        base_where += " AND jobs.location ILIKE :country_filter"
        params["country_filter"] = f"%{country}%"

    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    async with AsyncSessionLocal() as session:
        count_res = await session.execute(
            text(f"SELECT COUNT(*) FROM jobs WHERE {base_where}"), params
        )
        total = count_res.scalar() or 0

        rows_res = await session.execute(
            text(f"SELECT jobs.* FROM jobs WHERE {base_where} ORDER BY jobs.created_at DESC LIMIT :limit OFFSET :offset"),
            params,
        )
        rows = rows_res.fetchall()

    jobs_list = [dict(r._mapping) for r in rows]
    return total, jobs_list[:limit]


async def get_job_api(job_id) -> Optional[dict]:
    """Get a single job by ID from PostgreSQL."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("SELECT * FROM jobs WHERE id = :id AND status = 'active'"),
            {"id": str(job_id)},
        )
        row = res.fetchone()
    return dict(row._mapping) if row else None


async def get_categories_api() -> dict:
    """Calculate counts dynamically for categories from PostgreSQL."""
    async with AsyncSessionLocal() as session:
        queries = {
            "ai_ml": "title ILIKE '%ai%' OR title ILIKE '%machine learning%' OR title ILIKE '%data scientist%'",
            "backend": "title ILIKE '%backend%' OR title ILIKE '%python%' OR title ILIKE '%java%' OR title ILIKE '%node%'",
            "frontend": "title ILIKE '%frontend%' OR title ILIKE '%react%' OR title ILIKE '%vue%' OR title ILIKE '%angular%'",
            "fullstack": "title ILIKE '%fullstack%' OR title ILIKE '%full-stack%' OR title ILIKE '%full stack%'",
            "data_science": "title ILIKE '%data%' OR title ILIKE '%analytics%'",
            "remote": "is_remote = true",
            "internship": "job_type = 'internship'",
        }

        counts = {}
        for key, condition in queries.items():
            res = await session.execute(
                text(f"SELECT COUNT(*) FROM jobs WHERE status = 'active' AND ({condition})")
            )
            counts[key] = res.scalar() or 0

    return counts


async def get_autocomplete_suggestions_api(query: str) -> dict:
    """Returns autocomplete suggestions for companies, roles, and categories."""
    if not query or len(query) < 2:
        return {"companies": [], "roles": [], "categories": []}

    query_lower = query.lower()

    # 1. Companies from aliases
    companies = []
    for alias, canonical in COMPANY_ALIASES.items():
        if query_lower in alias or query_lower in canonical.lower():
            if canonical not in companies:
                companies.append(canonical)

    # 2. Companies from database
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("SELECT DISTINCT name FROM companies WHERE name ILIKE :q LIMIT 5"),
            {"q": f"%{query}%"},
        )
        for row in res.fetchall():
            if row[0] and row[0] not in companies:
                companies.append(row[0])

    # 3. Roles
    roles = ["Software Engineer", "Backend Developer", "Frontend Developer", "Full Stack Developer", "Data Scientist", "Machine Learning Engineer", "Product Manager", "DevOps Engineer"]
    matched_roles = [r for r in roles if query_lower in r.lower()]

    # 4. Categories
    categories = ["Internship", "Remote", "Fresher", "Full-time"]
    matched_categories = [c for c in categories if query_lower in c.lower()]

    return {
        "companies": companies[:5],
        "roles": matched_roles[:5],
        "categories": matched_categories[:3]
    }
