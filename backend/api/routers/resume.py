import os
import uuid
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.connection import AsyncSessionLocal
from utils.redis import redis_client
from models import Profile, GeneratedResume
from utils.config import OUTPUTS_DIR
from ai.resume_builder import generate_resume_content, generate_cover_letter_content
from ai.docx_generator import create_resume_docx, create_cover_letter_docx
from ai.pdf_converter import docx_to_pdf

router = APIRouter(prefix="/api/resume", tags=["resume"])

class GenerateRequest(BaseModel):
    session_id: str
    job_id: Optional[str] = None
    job_title: str = ""
    company_name: str = ""
    job_description: str = ""
    document_type: str = "both" # "resume", "cover_letter", "both"
    regenerate_with_projects: Optional[list[str]] = None
    existing_generation_id: Optional[str] = None

class FetchJobRequest(BaseModel):
    url: str

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def check_rate_limit(session_id: str):
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"resume_gen:{session_id}:{date_str}"
    
    count = await redis_client.get(key)
    if count and int(count) >= 5:
        raise HTTPException(status_code=429, detail="You've reached today's limit of 5 resume generations. Come back tomorrow or upgrade.")
        
    await redis_client.incr(key)
    # Set expiration to 24 hours if it's the first hit
    if count is None or int(count) == 0:
        await redis_client.expire(key, 86400)

@router.post("/fetch-job")
async def fetch_job(req: FetchJobRequest):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Mask as a standard browser to avoid basic blocks
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
            response = await client.get(req.url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            html = response.text
            
            soup = BeautifulSoup(html, "html.parser")
            
            title = ""
            company = ""
            description = ""
            
            # 1. Try LD+JSON schema.org/JobPosting
            ld_jsons = soup.find_all("script", type="application/ld+json")
            for script in ld_jsons:
                try:
                    data = json.loads(script.string)
                    # Handle both single objects and arrays of objects
                    if isinstance(data, list):
                        items = data
                    else:
                        items = [data]
                        
                    for item in items:
                        if item.get("@type") == "JobPosting":
                            title = item.get("title", "")
                            description = item.get("description", "")
                            # Cleanup HTML from description if it's there
                            if description:
                                description = BeautifulSoup(description, "html.parser").get_text(separator="\n")
                            hiring_org = item.get("hiringOrganization", {})
                            if isinstance(hiring_org, dict):
                                company = hiring_org.get("name", "")
                            break
                except Exception:
                    continue
                if title and description:
                    break
                    
            if not title:
                title = soup.title.string if soup.title else ""
                
            if not description:
                # 2. Fallback to <main> or <article>
                main_elem = soup.find("main") or soup.find("article")
                if main_elem:
                    description = main_elem.get_text(separator="\n", strip=True)
                else:
                    # 3. Fallback to longest block of text if no main
                    # Try finding the div with the most text
                    divs = soup.find_all("div")
                    longest_div = max(divs, key=lambda d: len(d.get_text(strip=True)) if d else 0, default=None)
                    if longest_div:
                        description = longest_div.get_text(separator="\n", strip=True)

            return {
                "title": title.strip(),
                "company": company.strip(),
                "description": description.strip()
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch job: {str(e)}")

@router.post("/generate")
async def generate_resume(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(req.session_id)
    
    # 1. Fetch Profile
    stmt = select(Profile).where(Profile.session_id == req.session_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=400, detail="Profile not found. Please set up your profile first.")
        
    profile_dict = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "professional_summary": profile.professional_summary,
        "education": profile.education or [],
        "experiences": profile.experiences or [],
        "projects": profile.projects or [],
        "skills": profile.skills or {}
    }
    profile_json = json.dumps(profile_dict, default=str)
    
    # Pass raw resume text to AI if available
    if getattr(profile, "raw_resume_text", None):
        profile_dict["raw_resume_text"] = profile.raw_resume_text
        profile_json = json.dumps(profile_dict, default=str)
    
    generation_id = str(uuid.uuid4())
    match_score = 0
    ats_keywords = []
    selected_projects = []
    docx_url = None
    cover_letter_url = None
    tailored_data = {}
    
    if req.document_type in ["resume", "both"]:
        # Cheap regeneration check
        if req.existing_generation_id and req.regenerate_with_projects is not None:
            tailored_json = await redis_client.get(f"gen_resume_data:{req.existing_generation_id}")
            if not tailored_json:
                raise HTTPException(status_code=404, detail="Original generation data expired. Please regenerate from scratch.")
            tailored_data = json.loads(tailored_json)
            # Override selected projects with the user's subset
            tailored_data["selected_projects"] = req.regenerate_with_projects
            
            # Inherit metrics
            match_score = tailored_data.get("match_score", 0)
            ats_keywords = tailored_data.get("ats_keywords", [])
            selected_projects = req.regenerate_with_projects
            
            docx_path = create_resume_docx(profile_dict, tailored_data, req.company_name)
            docx_filename = os.path.basename(docx_path)
            docx_url = f"/api/resume/download/{docx_filename}"
            
            await redis_client.setex(f"gen_resume_path:{req.existing_generation_id}", 3600, docx_path)
            generation_id = req.existing_generation_id
        else:
            tailored_data = await generate_resume_content(
                profile_json, 
                req.job_title, 
                req.company_name, 
                req.job_description
            )
            match_score = tailored_data.get("match_score", 0)
            ats_keywords = tailored_data.get("ats_keywords", [])
            selected_projects = tailored_data.get("selected_projects", [])
            
            # Save raw data to redis to allow cheap regeneration later
            await redis_client.setex(f"gen_resume_data:{generation_id}", 3600, json.dumps(tailored_data))
            
            docx_path = create_resume_docx(profile_dict, tailored_data, req.company_name)
            docx_filename = os.path.basename(docx_path)
            docx_url = f"/api/resume/download/{docx_filename}"
            
            # Save filepath to redis for pdf confirmation
            await redis_client.setex(f"gen_resume_path:{generation_id}", 3600, docx_path)
            
            # Store history permanently in DB
            new_history = GeneratedResume(
                id=uuid.UUID(generation_id),
                session_id=req.session_id,
                job_url=req.job_id,  # using job_id field for url/id
                job_title=req.job_title,
                company_name=req.company_name,
                ats_score_before=tailored_data.get("ats_score_before"),
                ats_score_after=tailored_data.get("ats_score_after"),
                keywords_missing=tailored_data.get("keywords_missing", []),
                keywords_added=tailored_data.get("keywords_added", []),
                recommendations=tailored_data.get("recommendations", []),
                docx_url=docx_url
            )
            db.add(new_history)
            await db.commit()

    if req.document_type in ["cover_letter", "both"] and not req.regenerate_with_projects:
        # Don't regenerate cover letter on cheap regeneration
        cl_content = await generate_cover_letter_content(
            profile_json,
            profile.full_name or "Candidate",
            req.job_title,
            req.company_name,
            req.job_description
        )
        cl_path = create_cover_letter_docx(profile_dict, cl_content, req.company_name)
        cl_filename = os.path.basename(cl_path)
        cover_letter_url = f"/api/resume/download/{cl_filename}"
        
        await redis_client.setex(f"gen_cl_path:{generation_id}", 3600, cl_path)
    elif req.document_type in ["cover_letter", "both"] and req.regenerate_with_projects and req.existing_generation_id:
        # If it's a cheap regen, preserve the old cover letter URL if it existed
        old_cl_path = await redis_client.get(f"gen_cl_path:{req.existing_generation_id}")
        if old_cl_path:
            cover_letter_url = f"/api/resume/download/{os.path.basename(old_cl_path)}"

    return {
        "generation_id": generation_id,
        "match_score": match_score,
        "ats_score_before": tailored_data.get("ats_score_before", 0),
        "ats_score_after": tailored_data.get("ats_score_after", match_score),
        "keywords_present": tailored_data.get("keywords_present", []),
        "keywords_missing": tailored_data.get("keywords_missing", []),
        "keywords_added": tailored_data.get("keywords_added", []),
        "recommendations": tailored_data.get("recommendations", []),
        "sections_to_emphasize": tailored_data.get("sections_to_emphasize", []),
        "ats_keywords": ats_keywords,
        "selected_projects": selected_projects,
        "docx_url": docx_url,
        "cover_letter_docx_url": cover_letter_url,
        "pdf_url": None,
        "cover_letter_pdf_url": None,
        "status": "ready_for_review"
    }

@router.post("/confirm/{generation_id}")
async def confirm_generation(generation_id: str):
    resume_path = await redis_client.get(f"gen_resume_path:{generation_id}")
    cl_path = await redis_client.get(f"gen_cl_path:{generation_id}")
    
    response = {}
    
    if resume_path and os.path.exists(resume_path):
        pdf_path = docx_to_pdf(resume_path)
        pdf_filename = os.path.basename(pdf_path)
        response["pdf_url"] = f"/api/resume/download/{pdf_filename}"
        
    if cl_path and os.path.exists(cl_path):
        cl_pdf_path = docx_to_pdf(cl_path)
        cl_pdf_filename = os.path.basename(cl_pdf_path)
        response["cover_letter_pdf_url"] = f"/api/resume/download/{cl_pdf_filename}"
        
    if not response:
        raise HTTPException(status_code=404, detail="Generation not found or files expired")
        
    return response

@router.get("/download/{filename}")
async def download_file(filename: str):
    filepath = OUTPUTS_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    media_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(filepath, media_type=media_type, filename=filename)

@router.get("/history/{session_id}")
async def get_resume_history(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(GeneratedResume).where(GeneratedResume.session_id == session_id).order_by(GeneratedResume.created_at.desc())
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    return [
        {
            "id": str(h.id),
            "job_url": h.job_url,
            "job_title": h.job_title,
            "company_name": h.company_name,
            "ats_score_before": h.ats_score_before,
            "ats_score_after": h.ats_score_after,
            "docx_url": h.docx_url,
            "pdf_url": h.pdf_url,
            "created_at": h.created_at
        } for h in history
    ]
