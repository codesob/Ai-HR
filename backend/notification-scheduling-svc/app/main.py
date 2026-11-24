from shared.core.app import create_service_app

from app.api.notifications import router as notifications_router

app = create_service_app("notification-scheduling-svc", [notifications_router])
