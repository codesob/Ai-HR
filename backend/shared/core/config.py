from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    app_name: str = "AI-HR Platform"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "dev-secret-change-in-production-min-32"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite+aiosqlite:///./aihr.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    openai_api_key: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    embedding_model: str = "all-MiniLM-L6-v2"
    upload_dir: str = "uploads"
    knowledge_dir: str = "knowledge"
    resume_service_url: str = "http://resume-parsing-svc:8000"
    matching_service_url: str = "http://matching-engine-svc:8000"
    interview_service_url: str = "http://interview-assistant-svc:8000"
    analytics_service_url: str = "http://analytics-dashboard-svc:8000"
    hr_ops_service_url: str = "http://hr-ops-onboarding-svc:8000"
    chatbot_service_url: str = "http://chatbot-rag-assistant-svc:8000"
    payroll_service_url: str = "http://payroll-automation-svc:8000"
    notification_service_url: str = "http://notification-scheduling-svc:8000"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    audit_log_path: str = "audit.log"
    storage_backend: str = "local"
    s3_bucket: str | None = None
    s3_region: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def cors_origin_regex(self) -> str:
        return r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$"


@lru_cache
def get_settings() -> Settings:
    return Settings()
