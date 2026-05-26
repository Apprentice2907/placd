import sys
import re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Optional, List, Tuple
from db.database import get_connection, get_job_stats

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
        intents['text'] = '' # Clear text if it perfectly matches a company alias
        
    return intents

def get_jobs_api(
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
    conn = get_connection()
    
    # Parse search intents
    intents = parse_search_query(search) if search else {'company': None, 'role': None, 'skill': None, 'collection': None, 'text': ''}
    
    base_query = "FROM jobs WHERE canonical_job_id IS NULL AND removed_at IS NULL"
    params = []
    
    fts_conditions = []
    if intents['text']:
        fts_conditions.append(intents['text'])
    if intents['role']:
        fts_conditions.append(intents['role'])
    if intents['skill']:
        fts_conditions.append(intents['skill'])
        
    fts_query = " ".join(fts_conditions)
    
    if fts_query:
        base_query = f"FROM jobs_fts JOIN jobs ON jobs.id = jobs_fts.rowid WHERE jobs_fts MATCH ? AND canonical_job_id IS NULL"
        params.append(fts_query)
        
    conditions = []
    if intents['company']:
        conditions.append("jobs.company LIKE ?")
        params.append(f"%{intents['company']}%")
        
    if intents.get('collection'):
        collection_val = intents['collection'].lower()
        if collection_val == 'faang':
            conditions.append("(company_type = 'faang' OR company_tags LIKE '%FAANG%')")
        elif collection_val == 'ai_companies' or collection_val == 'ai':
            conditions.append("(company_type = 'ai_company' OR company_tags LIKE '%AI%')")
        elif collection_val == 'unicorn_startups' or collection_val == 'unicorn':
            conditions.append("(company_type = 'unicorn' OR company_tags LIKE '%Unicorn%')")
        elif collection_val == 'remote_companies' or collection_val == 'remote':
            conditions.append("(company_type = 'remote' OR company_tags LIKE '%Remote%')")
        elif collection_val == 'research_labs' or collection_val == 'research':
            conditions.append("(company_tags LIKE '%Research%')")
        
    if remote: conditions.append("is_remote = 1")
    if internship: conditions.append("is_internship = 1")
    if fulltime: conditions.append("is_fulltime = 1")
    if research: conditions.append("is_research = 1")
    if new_grad: conditions.append("is_new_grad = 1")
    if hybrid: conditions.append("is_hybrid = 1")
    
    if experience:
        if experience == "Fresher":
            conditions.append("is_fresher = 1")
        else:
            conditions.append("experience = ?")
            params.append(experience)
    else:
        # Hide senior roles by default if no explicit seniority is selected
        conditions.append("is_senior = 0")
            
    if company_tier:
        conditions.append("company_tags LIKE ?")
        params.append(f"%{company_tier}%")
        
    if city:
        conditions.append("(city = ? OR locations LIKE ?)")
        params.extend([city, f"%\"{city}\"%"])
        
    if country:
        conditions.append("country = ?")
        params.append(country)

    if min_score > 0:
        conditions.append("match_score >= ?")
        params.append(min_score)

    if conditions:
        if "WHERE" in base_query:
            base_query += " AND " + " AND ".join(conditions)
        else:
            base_query += " WHERE " + " AND ".join(conditions)

    # Count total
    count_query = f"SELECT COUNT(*) {base_query}"
    total = conn.execute(count_query, params).fetchone()[0]

    # Fetch rows
    # We fetch more rows if there's a search, so we can post-process ranking
    fetch_limit = limit * 2 if (search and total > limit) else limit
    offset = (page - 1) * limit
    
    order_clause = "ORDER BY coalesce(posted_date_normalized, enrichment_timestamp) DESC"
    data_query = f"SELECT jobs.* {base_query} {order_clause} LIMIT ? OFFSET ?"
        
    params.extend([fetch_limit, offset])
    rows = conn.execute(data_query, params).fetchall()
    conn.close()
    
    jobs_list = [dict(row) for row in rows]
    
    # Return strictly the limit requested
    return total, jobs_list[:limit]


def get_job_api(job_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ? AND canonical_job_id IS NULL AND removed_at IS NULL", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_categories_api() -> dict:
    """Calculate counts dynamically for categories."""
    conn = get_connection()
    
    def count_query(condition: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM jobs WHERE canonical_job_id IS NULL AND removed_at IS NULL AND ({condition})").fetchone()[0]
    
    counts = {
        "ai_ml": count_query("title LIKE '%ai%' OR title LIKE '%machine learning%' OR title LIKE '%data scientist%'"),
        "backend": count_query("title LIKE '%backend%' OR title LIKE '%python%' OR title LIKE '%java%' OR title LIKE '%node%'"),
        "frontend": count_query("title LIKE '%frontend%' OR title LIKE '%react%' OR title LIKE '%vue%' OR title LIKE '%angular%'"),
        "fullstack": count_query("title LIKE '%fullstack%' OR title LIKE '%full-stack%' OR title LIKE '%full stack%'"),
        "data_science": count_query("title LIKE '%data%' OR title LIKE '%analytics%'"),
        "remote": count_query("is_remote = 1"),
        "internship": count_query("is_internship = 1")
    }
    
    conn.close()
    return counts

def get_autocomplete_suggestions_api(query: str) -> dict:
    """Returns autocomplete suggestions for companies, roles, and categories."""
    if not query or len(query) < 2:
        return {"companies": [], "roles": [], "categories": []}
        
    query_lower = query.lower()
    
    # 1. Companies
    companies = []
    for alias, canonical in COMPANY_ALIASES.items():
        if query_lower in alias or query_lower in canonical.lower():
            if canonical not in companies:
                companies.append(canonical)
                
    # Also fetch from DB for top companies matching query
    conn = get_connection()
    db_companies = conn.execute(
        "SELECT DISTINCT company FROM jobs WHERE canonical_job_id IS NULL AND removed_at IS NULL AND company LIKE ? LIMIT 5", 
        (f"%{query}%",)
    ).fetchall()
    
    for row in db_companies:
        company_name = row[0]
        if company_name and company_name not in companies:
            companies.append(company_name)
            
    # 2. Roles
    roles = ["Software Engineer", "Backend Developer", "Frontend Developer", "Full Stack Developer", "Data Scientist", "Machine Learning Engineer", "Product Manager", "DevOps Engineer"]
    matched_roles = [r for r in roles if query_lower in r.lower()]
    
    # 3. Categories
    categories = ["Internship", "Remote", "Fresher", "Full-time"]
    matched_categories = [c for c in categories if query_lower in c.lower()]
    
    conn.close()
    
    return {
        "companies": companies[:5],
        "roles": matched_roles[:5],
        "categories": matched_categories[:3]
    }
