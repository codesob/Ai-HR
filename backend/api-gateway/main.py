from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import httpx

from shared.api.auth import router as auth_router
from shared.api.rate_limit import enforce_rate_limit
from shared.core.config import get_settings
from shared.db.init import init_database
from shared.services.audit import write_audit_event

app = FastAPI(title="API Gateway")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix=settings.api_v1_prefix)


SERVICES = {
    "resumes": settings.resume_service_url,
    "jobs": settings.matching_service_url,
    "applications": settings.matching_service_url,
    "interviews": settings.interview_service_url,
    "analytics": settings.analytics_service_url,
    "onboarding": settings.hr_ops_service_url,
    "leave": settings.hr_ops_service_url,
    "chat": settings.chatbot_service_url,
    "payroll": settings.payroll_service_url,
    "notifications": settings.notification_service_url,
}


@app.on_event("startup")
async def startup() -> None:
    await init_database()


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    await enforce_rate_limit(request)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith(settings.api_v1_prefix):
        await write_audit_event(
            actor=request.headers.get("x-user-email"),
            action=request.method,
            resource=request.url.path,
            status_code=response.status_code,
            metadata={"query": str(request.url.query), "client": request.client.host if request.client else None},
        )
    return response


@app.post(f"{settings.api_v1_prefix}/graphql")
async def graphql(request: Request):
    body = await request.json()
    query = str(body.get("query", "")).lower()
    async with httpx.AsyncClient() as client:
        if "jobs" in query:
            response = await client.get(f"{settings.matching_service_url}{settings.api_v1_prefix}/jobs")
            return {"data": {"jobs": response.json()}}
        if "analytics" in query:
            response = await client.get(
                f"{settings.analytics_service_url}{settings.api_v1_prefix}/analytics/hiring",
                headers={key: value for key, value in request.headers.items() if key.lower() != "host"},
            )
            return {"data": {"analytics": response.json()}}
    return JSONResponse(
        {"errors": [{"message": "Supported MVP queries: jobs, analytics"}]},
        status_code=400,
    )


@app.websocket(f"{settings.api_v1_prefix}/ws/notifications")
async def notification_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "connected", "message": "Notification stream ready"})
        while True:
            message = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "message": message})
    except WebSocketDisconnect:
        return


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(path: str, request: Request):
    root_path = path.split("/")[2] if path.startswith("api/v1/") else path.split("/")[0]
    
    target_service = SERVICES.get(root_path)
    if not target_service:
        return JSONResponse({"error": "Service not found"}, status_code=404)
        
    url = f"{target_service}/{path}"
    
    async with httpx.AsyncClient() as client:
        try:
            req_body = await request.body()
            headers = dict(request.headers)
            headers.pop("host", None)
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=req_body,
                params=request.query_params
            )
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return JSONResponse(content=response.json(), status_code=response.status_code)
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type=content_type or None,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
