from fastapi import APIRouter
from app.api.schemas import AiMissionRecommendRequest, AiMissionRecommendResponse
from app.api.services import get_daily_missions_service

router = APIRouter(prefix="/ai", tags=["Daily Missions"])

@router.post("/missions/daily", response_model=AiMissionRecommendResponse)
async def create_daily_missions(request: AiMissionRecommendRequest):
    return await get_daily_missions_service(request)