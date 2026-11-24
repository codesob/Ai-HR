from shared.core.app import create_service_app

from app.api.applications import router as applications_router, score_unscored_applications
from app.api.jobs import router as jobs_router

app = create_service_app(
    "matching-engine-svc", [applications_router, jobs_router], on_startup=[score_unscored_applications]
)
