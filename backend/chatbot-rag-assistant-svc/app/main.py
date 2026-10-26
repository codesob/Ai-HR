import asyncio

from shared.core.app import create_service_app
from shared.services.rag_chatbot import seed_knowledge_base

from app.api.chat import router as chat_router


async def seed_knowledge() -> None:
    await asyncio.to_thread(seed_knowledge_base)


app = create_service_app("chatbot-rag-assistant-svc", [chat_router], on_startup=[seed_knowledge])
