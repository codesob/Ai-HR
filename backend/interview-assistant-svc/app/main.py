from shared.core.app import create_service_app

from app.api.interviews import router as interviews_router

app = create_service_app("interview-assistant-svc", [interviews_router])
