from shared.core.app import create_service_app

from app.api.resumes import router as resumes_router

app = create_service_app("resume-parsing-svc", [resumes_router])
