import math
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select
from typing import Optional, List, Dict, Any

from db.connection import get_db_session
from models import Opportunity

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

@router.get("")
async def search_opportunities(
    q: Optional[str] = None,
    type: Optional[str] = Query(None, description="scholarship|fellowship|internship|exchange_program|conference|competition|training"),
    country: Optional[str] = None,
    funding: Optional[str] = Query(None, description="fully_funded|paid|partially_funded"),
    deadline_within_days: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    offset = (page - 1) * limit
    
    # Base query
    stmt = select(Opportunity)
    count_stmt = select(func.count(Opportunity.id))

    # Apply filters
    if type:
        stmt = stmt.where(Opportunity.opportunity_type == type)
        count_stmt = count_stmt.where(Opportunity.opportunity_type == type)
    if country:
        stmt = stmt.where(Opportunity.country.ilike(f"%{country}%"))
        count_stmt = count_stmt.where(Opportunity.country.ilike(f"%{country}%"))
    if funding:
        stmt = stmt.where(Opportunity.funding_type == funding)
        count_stmt = count_stmt.where(Opportunity.funding_type == funding)
    if deadline_within_days is not None:
        stmt = stmt.where(Opportunity.deadline <= func.now() + text(f"INTERVAL '{deadline_within_days} days'"))
        stmt = stmt.where(Opportunity.deadline >= func.now())
        count_stmt = count_stmt.where(Opportunity.deadline <= func.now() + text(f"INTERVAL '{deadline_within_days} days'"))
        count_stmt = count_stmt.where(Opportunity.deadline >= func.now())
        
    if q:
        # Simple ilike search if not using FTS. For production FTS is better, but since pgvector/GIN 
        # is used for tags, we can just do basic string matching here or tsvector raw sql
        from sqlalchemy import or_ as sa_or
        search_filter = sa_or(
            Opportunity.title.ilike(f"%{q}%"),
            Opportunity.description.ilike(f"%{q}%")
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    # Ordering
    # Sort by deadline ASC if present, then first_seen_at DESC
    stmt = stmt.order_by(Opportunity.deadline.asc().nulls_last(), Opportunity.first_seen_at.desc())

    # Pagination
    stmt = stmt.offset(offset).limit(limit)

    # Execute
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar()

    result = await db.execute(stmt)
    opportunities = result.scalars().all()

    # Convert to dict
    opp_list = []
    for opp in opportunities:
        opp_dict = {
            "id": str(opp.id),
            "source_url": opp.source_url,
            "title": opp.title,
            "description_snippet": opp.description[:200] if opp.description else None,
            "opportunity_type": opp.opportunity_type,
            "funding_type": opp.funding_type,
            "country": opp.country,
            "organization": opp.organization,
            "deadline": str(opp.deadline) if opp.deadline else None,
            "tags": opp.tags,
            "source_name": opp.source_name,
            "status": opp.status,
            "first_seen_at": opp.first_seen_at.isoformat() if opp.first_seen_at else None
        }
        opp_list.append(opp_dict)

    return {
        "data": opp_list,
        "pagination": {
            "page": page,
            "per_page": limit,
            "total_items": total_count,
            "total_pages": math.ceil(total_count / limit) if total_count else 0
        }
    }

@router.get("/stats")
async def get_opportunities_stats(db: AsyncSession = Depends(get_db_session)):
    stats = {}
    
    # Total active vs expired
    res = await db.execute(select(Opportunity.status, func.count(Opportunity.id)).group_by(Opportunity.status))
    stats["by_status"] = {row[0]: row[1] for row in res.fetchall()}
    
    # By type
    res = await db.execute(select(Opportunity.opportunity_type, func.count(Opportunity.id)).group_by(Opportunity.opportunity_type))
    stats["by_type"] = {row[0]: row[1] for row in res.fetchall()}
    
    # By funding
    res = await db.execute(select(Opportunity.funding_type, func.count(Opportunity.id)).group_by(Opportunity.funding_type))
    stats["by_funding"] = {row[0]: row[1] for row in res.fetchall()}

    return stats

@router.get("/{id}")
async def get_opportunity(id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Opportunity).where(Opportunity.id == id)
    result = await db.execute(stmt)
    opp = result.scalar()
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    opp_dict = {
        "id": str(opp.id),
        "source_url": opp.source_url,
        "title": opp.title,
        "description": opp.description,
        "opportunity_type": opp.opportunity_type,
        "funding_type": opp.funding_type,
        "country": opp.country,
        "organization": opp.organization,
        "deadline": str(opp.deadline) if opp.deadline else None,
        "start_date": str(opp.start_date) if opp.start_date else None,
        "tags": opp.tags,
        "source_name": opp.source_name,
        "status": opp.status,
        "first_seen_at": opp.first_seen_at.isoformat() if opp.first_seen_at else None
    }
    
    return opp_dict
