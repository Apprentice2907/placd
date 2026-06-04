from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.connection import AsyncSessionLocal
from models import Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])

class ProfilePayload(BaseModel):
    session_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    professional_summary: Optional[str] = None
    education: Optional[List[Dict[str, Any]]] = None
    experiences: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    skills: Optional[Dict[str, List[str]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    achievements: Optional[List[Dict[str, Any]]] = None
    languages: Optional[List[Dict[str, Any]]] = None

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("")
async def upsert_profile(payload: ProfilePayload, db: AsyncSession = Depends(get_db)):
    stmt = select(Profile).where(Profile.session_id == payload.session_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    profile_data = payload.dict(exclude_unset=True)
    session_id = profile_data.pop("session_id")

    if profile:
        for k, v in profile_data.items():
            setattr(profile, k, v)
    else:
        profile = Profile(session_id=session_id, **profile_data)
        db.add(profile)

    await db.commit()
    return {"status": "success", "message": "Profile saved successfully"}

@router.get("/{session_id}")
async def get_profile(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Profile).where(Profile.session_id == session_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return profile

@router.delete("/{session_id}")
async def delete_profile(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Profile).where(Profile.session_id == session_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    await db.delete(profile)
    await db.commit()
    return {"status": "success", "message": "Profile deleted successfully"}
