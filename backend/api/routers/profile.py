from fastapi import APIRouter
from api.schemas import UserProfile
from db.database import get_user_profile, upsert_user_profile

router = APIRouter()

@router.get("/", response_model=UserProfile)
def get_profile():
    profile = get_user_profile()
    if not profile:
        return UserProfile()
    return profile

@router.put("/", response_model=UserProfile)
def update_profile(profile: UserProfile):
    upsert_user_profile(profile.model_dump(exclude_unset=True))
    return get_user_profile()
