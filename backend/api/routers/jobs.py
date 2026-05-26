from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..schemas import PaginatedJobsResponse, JobResponse
from ..services import get_jobs_api, get_job_api, get_autocomplete_suggestions_api

router = APIRouter()

@router.get("/", response_model=PaginatedJobsResponse)
def get_jobs(
    search: Optional[str] = Query(None, description="FTS5 search query"),
    remote: Optional[bool] = Query(None),
    internship: Optional[bool] = Query(None),
    fulltime: Optional[bool] = Query(None),
    research: Optional[bool] = Query(None),
    new_grad: Optional[bool] = Query(None),
    experience: Optional[str] = Query(None),
    hybrid: Optional[bool] = Query(None),
    company_tier: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_score: float = Query(0.0),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    total, jobs = get_jobs_api(
        search=search,
        remote=remote,
        internship=internship,
        fulltime=fulltime,
        research=research,
        new_grad=new_grad,
        experience=experience,
        hybrid=hybrid,
        company_tier=company_tier,
        city=city,
        country=country,
        min_score=min_score,
        page=page,
        limit=limit
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "jobs": jobs
    }

@router.get("/autocomplete")
def get_autocomplete(q: str = Query(..., min_length=1)):
    return get_autocomplete_suggestions_api(q)

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    job = get_job_api(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or is a duplicate")
    return job
