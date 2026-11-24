import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from shared.core.config import get_settings
from shared.core.logging import configure_logging, request_id_var
from shared.db.init import check_database, init_database

logger = logging.getLogger(__name__)

StartupHook = Callable[[], Awaitable[None]]


def install_request_context(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        # The 500 handler runs after the contextvar is reset, so keep the id on the request too.
        request.state.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None) or request_id_var.get()
        logger.exception(
            "Unhandled error", extra={"path": request.url.path, "method": request.method, "request_id": rid}
        )
        return JSONResponse(
            {"detail": "Internal server error", "request_id": rid},
            status_code=500,
            headers={"X-Request-ID": rid} if rid else None,
        )


def create_service_app(
    name: str,
    routers: Iterable[APIRouter],
    on_startup: Iterable[StartupHook] = (),
    on_shutdown: Iterable[StartupHook] = (),
) -> FastAPI:
    settings = get_settings()
    configure_logging(name, settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await init_database()
        for hook in on_startup:
            try:
                await hook()
            except Exception:
                # Optional dependencies (vector store, models) must not stop the service booting.
                logger.exception("Startup hook failed", extra={"hook": getattr(hook, "__name__", str(hook))})
        logger.info("Service started", extra={"environment": settings.environment})
        yield
        for hook in on_shutdown:
            await hook()

    app = FastAPI(
        title=name,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    install_request_context(app)
    for router in routers:
        app.include_router(router, prefix=settings.api_v1_prefix)

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok", "service": name}

    @app.get("/ready", include_in_schema=False)
    async def ready():
        if await check_database():
            return {"status": "ready", "service": name}
        return JSONResponse({"status": "unavailable", "service": name}, status_code=503)

    return app
