from shared.core.app import create_service_app

from app.api.leave import router as leave_router
from app.api.onboarding import router as onboarding_router

app = create_service_app("hr-ops-onboarding-svc", [leave_router, onboarding_router])
