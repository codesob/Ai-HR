import asyncio

from shared.core.app import create_service_app
from shared.services.agent.schedule import start_schedule, stop_schedule
from shared.services.rag_chatbot import seed_knowledge_base

from app.api.agent import router as agent_router
from app.api.chat import router as chat_router
from app.api.handbook import router as handbook_router


async def seed_knowledge() -> None:
    await asyncio.to_thread(seed_knowledge_base)


app = create_service_app(
    "chatbot-rag-assistant-svc",
    [chat_router, agent_router, handbook_router],
    on_startup=[seed_knowledge, start_schedule],
    on_shutdown=[stop_schedule],
)
