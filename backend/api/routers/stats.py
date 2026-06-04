import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter
from ..schemas import StatsResponse, CategoryCountsResponse
from ..services import get_categories_api
from db.database import get_job_stats

router = APIRouter()

@router.get("/", response_model=StatsResponse)
def get_stats():
    raw_stats = get_job_stats()
    
    # Transform raw stats into schema format
    sources = {}
    statuses = {}
    total = raw_stats.get("total", 0)
    avg_score = raw_stats.get("avg_match_score", 0.0)
    
    for key, val in raw_stats.items():
        if key.startswith("source_"):
            sources[key.replace("source_", "")] = val
        elif key.startswith("status_"):
            statuses[key.replace("status_", "")] = val
            
    return {
        "total_jobs": total,
        "sources": sources,
        "statuses": statuses,
        "avg_match_score": avg_score
    }

@router.get("/categories", response_model=CategoryCountsResponse)
async def get_categories():
    return await get_categories_api()
