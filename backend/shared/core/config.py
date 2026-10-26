from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"

INSECURE_SECRET_KEYS = {
    "",
    "dev-secret-change-in-production-min-32",
    "change-me-in-production",
    "your-secret-key-min-32-chars",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    app_name: str = "AI-HR Platform"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    secret_key: str = "dev-secret-change-in-production-min-32"
    access_token_expire_minutes: int = 60 * 8
    invite_expire_hours: int = 72

    database_url: str = "sqlite+aiosqlite:///./aihr.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    # Schema is created by Alembic in production; dev/test may bootstrap it directly.
    auto_create_schema: bool | None = None
    seed_demo_data: bool | None = None

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    embedding_model: str = "all-MiniLM-L6-v2"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    nvidia_api_key: str | None = None
    nvidia_reranker_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2"
    nvidia_api_endpoint: str = "https://integrate.api.nvidia.com/v1"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Allow LAN origins in development only; never in production.
    cors_allow_lan: bool = True
    frontend_url: str = "http://localhost:3000"

    upload_dir: str = "uploads"
    max_upload_mb: int = 5
    knowledge_dir: str = "knowledge"
    storage_backend: Literal["local", "s3"] = "local"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "AI-HR <no-reply@example.com>"
    smtp_use_tls: bool = True

    resume_service_url: str = "http://resume-parsing-svc:8000"
    matching_service_url: str = "http://matching-engine-svc:8000"
    interview_service_url: str = "http://interview-assistant-svc:8000"
    analytics_service_url: str = "http://analytics-dashboard-svc:8000"
    hr_ops_service_url: str = "http://hr-ops-onboarding-svc:8000"
    chatbot_service_url: str = "http://chatbot-rag-assistant-svc:8000"
    payroll_service_url: str = "http://payroll-automation-svc:8000"
    notification_service_url: str = "http://notification-scheduling-svc:8000"
    upstream_timeout_seconds: float = 60.0

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 10
    # Only honour X-Forwarded-For when running behind a trusted reverse proxy.
    trust_proxy_headers: bool = False

    @model_validator(mode="after")
    def _apply_environment_defaults(self) -> "Settings":
        is_prod = self.environment == "production"
        if self.auto_create_schema is None:
            self.auto_create_schema = not is_prod
        if self.seed_demo_data is None:
            self.seed_demo_data = self.environment == "development"
        if is_prod:
            if self.secret_key in INSECURE_SECRET_KEYS or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a random value of at least 32 characters in production")
            if self.database_url.startswith("sqlite"):
                raise ValueError("SQLite is not supported in production; set DATABASE_URL to PostgreSQL")
            if self.storage_backend == "s3" and not self.s3_bucket:
                raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")
            self.cors_allow_lan = False
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or [self.frontend_url]

    @property
    def cors_origin_regex(self) -> str | None:
        if not self.cors_allow_lan:
            return None
        return r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$"


@lru_cache
def get_settings() -> Settings:
    return Settings()
