from fastapi import APIRouter
from app.api.schemas import AiDailyAnalysisRequest, AiDailyAnalysisResponse
from app.api.services import get_daily_feedback_service

router = APIRouter(prefix="/ai", tags=["Daily Analysis"])

@router.post("/analysis/daily", response_model=AiDailyAnalysisResponse)
async def create_daily_feedback(request: AiDailyAnalysisRequest):
    return await get_daily_feedback_service(request)