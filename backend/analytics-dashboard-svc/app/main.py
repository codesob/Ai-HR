from shared.core.app import create_service_app

from app.api.analytics import router as analytics_router

app = create_service_app("analytics-dashboard-svc", [analytics_router])
