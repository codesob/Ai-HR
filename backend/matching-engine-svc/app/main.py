from shared.core.app import create_service_app

from app.api.applications import router as applications_router
from app.api.jobs import router as jobs_router

app = create_service_app("matching-engine-svc", [applications_router, jobs_router])
