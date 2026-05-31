from fastapi import APIRouter

from shared.schemas.common import ChatMessage, ChatResponse
from shared.services.rag_chatbot import chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def hr_chat(payload: ChatMessage):
    reply, sources, session_id = chat(payload.message, payload.session_id)
    return ChatResponse(reply=reply, sources=sources, session_id=session_id)
