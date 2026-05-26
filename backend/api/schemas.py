from typing import List, Optional
from pydantic import BaseModel

class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    job_type: str
    salary: str
    description: str
    url: str
    source: str
    skills: str
    match_score: float
    status: str
    scraped_at: str
    apply_url: str
    hiring_status: str
    duration: str
    experience: Optional[str] = None
    posted_date: Optional[str] = None
    posted_date_normalized: Optional[str] = None
    final_score: float
    ranking_breakdown: str
    is_enriched: bool
    is_remote: bool
    is_hybrid: bool
    is_fulltime: bool
    is_internship: bool
    is_fresher: bool
    merged_sources: str
    source_count: int
    company_tags: Optional[str] = None
    is_paid: Optional[int] = None

    class Config:
        from_attributes = True

class PaginatedJobsResponse(BaseModel):
    total: int
    page: int
    limit: int
    jobs: List[JobResponse]

class StatsResponse(BaseModel):
    total_jobs: int
    sources: dict[str, int]
    statuses: dict[str, int]
    avg_match_score: float

class CategoryCountsResponse(BaseModel):
    ai_ml: int
    backend: int
    frontend: int
    fullstack: int
    data_science: int
    remote: int
    internship: int

class UserProfile(BaseModel):
    education_year: Optional[int] = None
    degree: Optional[str] = ""
    skills: Optional[str] = ""
    preferred_roles: Optional[str] = ""
    remote_preference: Optional[bool] = False
    expected_salary: Optional[str] = ""
    is_fresher_seeking: Optional[bool] = False
    is_internship_seeking: Optional[bool] = False
    
    class Config:
        from_attributes = True
