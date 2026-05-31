from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.core.config import get_settings
from shared.db.init import init_database

from app.api.interviews import router as interviews_router

settings = get_settings()
app = FastAPI(title="interview-assistant-svc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_v1_prefix
app.include_router(interviews_router, prefix=prefix)


@app.on_event("startup")
async def startup() -> None:
    await init_database()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "interview-assistant-svc"}
