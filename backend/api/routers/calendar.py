import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text
from db.connection import AsyncSessionLocal

router = APIRouter()

@router.get("/")
async def get_calendar(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month),
    category: str = Query("all"),
    view: str = Query("month")
):
    """
    Fetch hiring calendar events merged from manually curated windows
    and dynamically extracted job/opportunity deadlines.
    """
    bind_params = {"year": year, "month": month}
    
    # Optional Category filtering mapping
    # Assuming 'faang', 'hft', 'ai_lab', 'startup', 'india' match DB
    # 'internship', 'new_grad', 'remote' apply to jobs
    # 'scholarship', 'fellowship' apply to opportunities
    
    category_filter = ""
    if category != "all":
        if category in ['faang', 'hft', 'ai_lab', 'startup', 'india']:
            category_filter = "AND w.category = :category"
        elif category in ['internship', 'new_grad', 'remote']:
            pass # We'll handle this in jobs query later
        elif category in ['scholarship', 'fellowship']:
            pass # We'll handle this in opportunities query later
        bind_params["category"] = category

    events = []
    
    async with AsyncSessionLocal() as session:
        # 1. Manually curated company_hiring_windows
        windows_sql = f"""
            SELECT 
                id::text, 
                event_date as date, 
                company_name as company, 
                window_type || 's' as type, 
                category, 
                source_url, 
                verified,
                notes as title
            FROM company_hiring_windows w
            WHERE EXTRACT(YEAR FROM event_date) = :year 
              AND EXTRACT(MONTH FROM event_date) = :month
              {category_filter}
        """
        win_res = await session.execute(text(windows_sql), bind_params)
        for r in win_res.fetchall():
            d = dict(r._mapping)
            # Default title
            if not d['title']:
                d['title'] = f"Hiring {d['type']}"
            events.append(d)

        # 2. Dynamic dates from jobs table
        # We group by company and month, finding earliest open and latest close
        job_filters = "WHERE status = 'active' "
        if category == "internship":
            job_filters += "AND is_internship = true "
        elif category == "new_grad":
            job_filters += "AND is_new_grad = true "
        elif category == "remote":
            job_filters += "AND is_remote = true "
            
        jobs_sql = f"""
            SELECT 
                c.name as company,
                MIN(COALESCE(j.application_open_date, j.first_seen_at::date)) as open_date,
                MAX(j.application_close_date) as close_date,
                COUNT(j.id) as job_count
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            {job_filters}
            GROUP BY c.name
        """
        # Execute jobs aggregation
        jobs_res = await session.execute(text(jobs_sql))
        for r in jobs_res.fetchall():
            d = dict(r._mapping)
            
            # Check Open Date
            open_dt = d['open_date']
            if open_dt and open_dt.year == year and open_dt.month == month:
                events.append({
                    "id": f"job-open-{d['company']}",
                    "date": open_dt,
                    "company": d['company'],
                    "title": "Application opens",
                    "type": "opens",
                    "category": category if category != "all" else "other",
                    "source_url": None,
                    "verified": False,
                    "job_count": d['job_count']
                })
                
            # Check Close Date
            close_dt = d['close_date']
            if close_dt and close_dt.year == year and close_dt.month == month:
                events.append({
                    "id": f"job-close-{d['company']}",
                    "date": close_dt,
                    "company": d['company'],
                    "title": "Deadline",
                    "type": "deadline",
                    "category": category if category != "all" else "other",
                    "source_url": None,
                    "verified": False,
                    "job_count": d['job_count']
                })

        # 3. Dynamic dates from opportunities table
        opp_filters = "WHERE status = 'active' AND deadline IS NOT NULL"
        if category == "scholarship":
            opp_filters += " AND opportunity_type = 'scholarship'"
        elif category == "fellowship":
            opp_filters += " AND opportunity_type = 'fellowship'"
            
        opp_sql = f"""
            SELECT 
                id::text,
                deadline as date,
                organization as company,
                title,
                source_url
            FROM opportunities
            {opp_filters}
            AND EXTRACT(YEAR FROM deadline) = :year 
            AND EXTRACT(MONTH FROM deadline) = :month
        """
        opp_res = await session.execute(text(opp_sql), {"year": year, "month": month})
        for r in opp_res.fetchall():
            d = dict(r._mapping)
            events.append({
                "id": f"opp-{d['id']}",
                "date": d['date'],
                "company": d['company'] or "Unknown",
                "title": d['title'],
                "type": "deadline",
                "category": category if category != "all" else "fellowship",
                "source_url": d['source_url'],
                "verified": True,
                "job_count": 1
            })

    # Deduplicate: if a company has multiple "opens" in the same day, prefer the curated one
    deduped = {}
    for ev in events:
        key = f"{ev['company']}-{ev['date']}-{ev['type']}"
        if key in deduped:
            # Prefer verified ones
            if ev.get('verified') and not deduped[key].get('verified'):
                deduped[key] = ev
            # Merge job_count
            deduped[key]['job_count'] = max(deduped[key].get('job_count', 0), ev.get('job_count', 0))
            if not deduped[key].get('source_url') and ev.get('source_url'):
                deduped[key]['source_url'] = ev['source_url']
        else:
            deduped[key] = ev

    return {
        "month": month,
        "year": year,
        "events": list(deduped.values()),
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }
