from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import re
from db.connection import AsyncSessionLocal

from scrapers.jd_scraper import scrape_jd, JDScrapeFailed
from services.resume_service import research_company_role, rewrite_resume

router = APIRouter(prefix="/api/resume", tags=["resume"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class ScrapeJDRequest(BaseModel):
    url: str

class ResearchRequest(BaseModel):
    company: str
    role: str
    jd_text: str

class RewriteRequest(BaseModel):
    profile: dict
    research: dict
    jd_text: str

@router.post("/scrape-jd")
async def api_scrape_jd(req: ScrapeJDRequest):
    try:
        jd_text = await scrape_jd(req.url)
        company = ""
        role = ""
        match = re.search(r"([A-Za-z\s]+)\s+at\s+([A-Za-z0-9\s]+)", jd_text[:200], re.IGNORECASE)
        if match:
            role = match.group(1).strip()
            company = match.group(2).strip()

        return {
            "success": True,
            "jd_text": jd_text,
            "detected_company": company,
            "detected_role": role
        }
    except JDScrapeFailed:
        return {"success": False, "fallback": True}
    except Exception as e:
        return {"success": False, "fallback": True}

@router.post("/research")
async def api_research(req: ResearchRequest, db = Depends(get_db)):
    # Note: Using session_id placeholder '1' for user_profile since we modified user_profile
    research_json = await research_company_role(req.company, req.role, req.jd_text, session_id="1", db_session=db)
    return research_json

@router.post("/rewrite")
async def api_rewrite(req: RewriteRequest):
    rewrite_json = await rewrite_resume(req.profile, req.research, req.jd_text)
    return rewrite_json
