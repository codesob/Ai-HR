from shared.core.app import create_service_app

from app.api.payroll import router as payroll_router

app = create_service_app("payroll-automation-svc", [payroll_router])
