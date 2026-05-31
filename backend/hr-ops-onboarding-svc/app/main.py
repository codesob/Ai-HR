from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.core.config import get_settings
from shared.db.init import init_database

from app.api.onboarding import router as onboarding_router

from app.api.leave import router as leave_router

settings = get_settings()
app = FastAPI(title="hr-ops-onboarding-svc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_v1_prefix
app.include_router(leave_router, prefix=prefix)

app.include_router(onboarding_router, prefix=prefix)


@app.on_event("startup")
async def startup() -> None:
    await init_database()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hr-ops-onboarding-svc"}
