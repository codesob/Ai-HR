from fastapi import APIRouter, Depends

from shared.api.deps import require_user
from shared.models.entities import User
from shared.schemas.common import ChatMessage, ChatResponse
from shared.services.rag_chatbot import chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def hr_chat(payload: ChatMessage, _: User = Depends(require_user)):
    reply, sources, session_id = await chat(payload.message, payload.session_id)
    return ChatResponse(reply=reply, sources=sources, session_id=session_id)
