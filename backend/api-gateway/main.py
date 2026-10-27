import logging

import httpx
import jwt
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from shared.api.auth import account_router, users_router
from shared.api.auth import router as auth_router
from shared.api.rate_limit import client_ip, is_rate_limited
from shared.core.app import create_service_app
from shared.core.config import get_settings
from shared.core.logging import request_id_var
from shared.core.security import decode_access_token
from shared.services.audit import flush_pending_audit_events, write_audit_event
from shared.services.sessions import ACCESS_COOKIE, REFRESH_COOKIE

logger = logging.getLogger(__name__)
settings = get_settings()

SERVICES = {
    "resumes": settings.resume_service_url,
    "jobs": settings.matching_service_url,
    "applications": settings.matching_service_url,
    "interviews": settings.interview_service_url,
    "screening": settings.interview_service_url,
    "analytics": settings.analytics_service_url,
    "onboarding": settings.hr_ops_service_url,
    "leave": settings.hr_ops_service_url,
    "chat": settings.chatbot_service_url,
    "agent": settings.chatbot_service_url,
    "handbook": settings.chatbot_service_url,
    "payroll": settings.payroll_service_url,
    "notifications": settings.notification_service_url,
}

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "host", "content-length", "content-encoding",
}

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.upstream_timeout_seconds, connect=5.0),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
    return _client


async def close_client() -> None:
    if _client is not None:
        await _client.aclose()


app = create_service_app(
    "api-gateway", [auth_router, users_router, account_router], on_shutdown=[close_client, flush_pending_audit_events]
)

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")
# Session upkeep is frequent and harmless, so it shares the general API limit instead of the strict sign-in one.
LENIENT_AUTH_PATHS = {f"{settings.api_v1_prefix}/auth/refresh", f"{settings.api_v1_prefix}/auth/logout"}


def _claims(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.cookies.get(ACCESS_COOKIE)
    if not token:
        return {}
    try:
        return decode_access_token(token)
    except jwt.PyJWTError:
        return {}


def _cross_site_cookie_request(request: Request) -> bool:
    """Cookies ride along on cross-site requests, so a cookie-authenticated write must come from our own origin."""
    if request.method not in UNSAFE or request.headers.get("authorization"):
        return False
    if ACCESS_COOKIE not in request.cookies and REFRESH_COOKIE not in request.cookies:
        return False
    origin = request.headers.get("origin")
    return not origin or not settings.origin_allowed(origin)


@app.middleware("http")
async def edge_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith(settings.api_v1_prefix) and request.method != "OPTIONS":
        if _cross_site_cookie_request(request):
            return JSONResponse({"detail": "Request origin not allowed"}, status_code=403)
        is_auth = (
            path.startswith(f"{settings.api_v1_prefix}/auth/") and request.method == "POST"
            and path not in LENIENT_AUTH_PATHS
        )
        limited = await is_rate_limited(
            request,
            bucket="auth" if is_auth else "api",
            limit=settings.auth_rate_limit_requests if is_auth else settings.rate_limit_requests,
        )
        if limited:
            return JSONResponse({"detail": "Too many requests"}, status_code=429,
                                headers={"Retry-After": str(settings.rate_limit_window_seconds)})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    if path.startswith(settings.api_v1_prefix) and request.method in UNSAFE:
        claims = _claims(request)
        await write_audit_event(
            actor=claims.get("email"),
            organization_id=claims.get("org_id"),
            action=request.method,
            resource=path,
            status_code=response.status_code,
            metadata={"client": client_ip(request)},
        )
    return response


# Added last so it is the outermost layer: rate-limit and error responses still carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.api_route(f"{settings.api_v1_prefix}/{{service}}{{rest:path}}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(service: str, rest: str, request: Request):
    target = SERVICES.get(service)
    if not target:
        return JSONResponse({"detail": "Not found"}, status_code=404)

    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    headers["x-request-id"] = request_id_var.get() or ""
    headers["x-forwarded-for"] = client_ip(request)
    try:
        upstream = await get_client().request(
            method=request.method,
            url=f"{target}{settings.api_v1_prefix}/{service}{rest}",
            headers=headers,
            content=await request.body(),
            params=request.query_params,
        )
    except httpx.TimeoutException:
        logger.warning("Upstream timeout", extra={"service": service})
        return JSONResponse({"detail": "Upstream service timed out"}, status_code=504)
    except httpx.HTTPError:
        logger.exception("Upstream unavailable", extra={"service": service})
        return JSONResponse({"detail": "Service temporarily unavailable"}, status_code=503)

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
