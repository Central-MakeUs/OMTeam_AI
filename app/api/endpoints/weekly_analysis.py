from fastapi import APIRouter
from app.api.schemas import WeeklyAnalysisRequest, UnifiedAIResponse
from app.api.services import get_weekly_analysis_service

router = APIRouter(prefix="/ai", tags=["Weekly Analysis"])

@router.post("/analysis/weekly", response_model=UnifiedAIResponse)
async def create_weekly_analysis(request: WeeklyAnalysisRequest):
    return await get_weekly_analysis_service(request)