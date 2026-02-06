from fastapi import APIRouter
from app.api.schemas import AiChatRequest, AiChatResponse
from app.api.services import handle_chat_message_service

router = APIRouter(prefix="/ai", tags=["Chat"])

@router.post("/chat/messages", response_model=AiChatResponse)
async def handle_chat_message(request: AiChatRequest):
    return await handle_chat_message_service(request)