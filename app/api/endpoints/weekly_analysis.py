from fastapi import APIRouter
from app.api.schemas import AiWeeklyAnalysisRequest, AiWeeklyAnalysisResponse
from app.api.services import get_weekly_analysis_service

router = APIRouter(prefix="/ai", tags=["Weekly Analysis"])

@router.post("/analysis/weekly", response_model=AiWeeklyAnalysisResponse)
async def create_weekly_analysis(request: AiWeeklyAnalysisRequest):
    return await get_weekly_analysis_service(request)