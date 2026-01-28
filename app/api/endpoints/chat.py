from fastapi import APIRouter
from app.api.schemas import ChatSessionRequest, ChatMessageRequest, UnifiedAIResponse
from app.api.services import create_chat_session_service, handle_chat_message_service

router = APIRouter(prefix="/ai", tags=["Chat"])

@router.post("/chat/sessions", response_model=UnifiedAIResponse)
async def create_chat_session(request: ChatSessionRequest):
    return await create_chat_session_service(request)

@router.post("/chat/messages", response_model=UnifiedAIResponse)
async def handle_chat_message(request: ChatMessageRequest):
    return await handle_chat_message_service(request)