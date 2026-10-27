import importlib
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
_tmp = tempfile.mkdtemp(prefix="aihr-test-")

# Must be set before any shared.* import builds the settings and engine.
os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL=f"sqlite+aiosqlite:///{Path(_tmp, 'test.db').as_posix()}",
    SECRET_KEY="test-secret-key-that-is-long-enough-123456",
    SEED_DEMO_DATA="false",
    UPLOAD_DIR=str(Path(_tmp, "uploads")),
    REDIS_URL="redis://127.0.0.1:1/0",
    RATE_LIMIT_REQUESTS="0",
    AUTH_RATE_LIMIT_REQUESTS="0",
    GROQ_API_KEY="",
    AGENT_SCREEN_NEW_APPLICATIONS="false",
    NVIDIA_API_KEY="",
    SMTP_HOST="",
)
sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from shared.db.session import Base, engine  # noqa: E402
import shared.models.entities  # noqa: E402,F401


def load_service(name: str):
    """Import <service>/app/main.py in isolation; every service uses the same top-level `app` package."""
    for mod in [m for m in sys.modules if m == "app" or m.startswith("app.") or m == "main"]:
        del sys.modules[mod]
    service_dir = str(BACKEND / name)
    sys.path.insert(0, service_dir)
    try:
        module = importlib.import_module("main" if name == "api-gateway" else "app.main")
    finally:
        sys.path.remove(service_dir)
    return module.app


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    import shared.services.embeddings as emb
    import shared.services.matching as matching

    def embed(text: str) -> list[float]:
        vec = [0.0] * emb.VECTOR_SIZE
        for i, ch in enumerate(text.lower()[:2000]):
            vec[(ord(ch) + i) % emb.VECTOR_SIZE] += 1.0
        return vec

    monkeypatch.setattr(emb, "embed_text", embed)
    monkeypatch.setattr(matching, "embed_text", embed)
    monkeypatch.setattr(emb, "upsert_vector", lambda *a, **k: None)
    for mod in list(sys.modules.values()):
        if getattr(mod, "upsert_vector", None) is not None and mod.__name__.startswith("app."):
            monkeypatch.setattr(mod, "upsert_vector", lambda *a, **k: None)


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


_apps: dict[str, object] = {}


def service_client(name: str) -> httpx.AsyncClient:
    if name not in _apps:
        _apps[name] = load_service(name)
    # Like a browser: keeps cookies and sends our own frontend's Origin.
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_apps[name]), base_url="http://test",
        headers={"Origin": "http://localhost:3000"},
    )


@pytest_asyncio.fixture
async def clients():
    names = [
        "api-gateway", "matching-engine-svc", "analytics-dashboard-svc", "payroll-automation-svc",
        "hr-ops-onboarding-svc", "interview-assistant-svc", "resume-parsing-svc", "notification-scheduling-svc",
    ]
    opened = {n: service_client(n) for n in names}
    yield opened
    for c in opened.values():
        await c.aclose()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def signup(gateway: httpx.AsyncClient, company: str, email: str) -> dict:
    r = await gateway.post("/api/v1/auth/signup", json={
        "company_name": company, "full_name": "Owner", "email": email, "password": "correct-horse-1",
    })
    assert r.status_code == 201, r.text
    return r.json()
