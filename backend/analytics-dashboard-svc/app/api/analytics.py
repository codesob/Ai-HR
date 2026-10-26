from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import User, UserRole
from shared.schemas.common import AnalyticsSummary
from shared.services.ai_insights_dashboard import (
    generate_dashboard_insights,
    get_employee_dashboard,
    get_hiring_dashboard,
    predict_hiring_needs,
)
from shared.services.analytics import get_hiring_analytics, get_org_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


async def _workforce(db: AsyncSession, organization_id: int) -> dict:
    staff = (await db.execute(
        select(User.is_active, User.created_at).where(
            User.organization_id == organization_id, User.role != UserRole.CANDIDATE
        )
    )).all()
    active = [created for is_active, created in staff if is_active]
    now = datetime.now(timezone.utc)
    tenure_months = [
        (now - (c if c.tzinfo else c.replace(tzinfo=timezone.utc))).days / 30.4 for c in active if c
    ]
    return {
        "retention_rate": round(len(active) / len(staff), 3) if staff else 1.0,
        "attrition_rate": round(1 - len(active) / len(staff), 3) if staff else 0.0,
        "avg_tenure_months": round(sum(tenure_months) / len(tenure_months), 1) if tenure_months else 0.0,
    }


@router.get("/hiring", response_model=AnalyticsSummary)
async def hiring_analytics(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    return await get_hiring_analytics(db, user.organization_id)


@router.get("/ai/dashboard")
async def ai_insights_dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    m = await get_org_metrics(db, user.organization_id)
    w = await _workforce(db, user.organization_id)
    hiring_metrics = {
        "applications": m["total_applications"],
        "interviews_scheduled": m["pending_interviews"],
        "recent_hires": m["recent_hires"],
        "conversion_rate": round(m["recent_hires"] / max(1, m["total_applications"]) * 100, 1),
    }
    employee_metrics = {
        "retention_rate": w["retention_rate"],
        "avg_tenure_months": w["avg_tenure_months"],
        "active_onboardings": m["active_onboardings"],
    }
    return await generate_dashboard_insights(hiring_metrics, employee_metrics)


@router.get("/ai/hiring-dashboard")
async def hiring_dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    m = await get_org_metrics(db, user.organization_id)
    return await get_hiring_dashboard(
        total_applications=m["total_applications"],
        pending_interviews=m["pending_interviews"],
        recent_hires=m["recent_hires"],
        average_time_to_hire=m["avg_time_to_hire_days"] or 0.0,
        acceptance_rate=m["offer_acceptance_rate"] or 0.0,
    )


@router.get("/ai/employee-dashboard")
async def employee_dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    m = await get_org_metrics(db, user.organization_id)
    w = await _workforce(db, user.organization_id)
    return await get_employee_dashboard(
        total_employees=m["headcount"],
        recent_onboardings=m["active_onboardings"],
        retention_rate=w["retention_rate"],
        avg_tenure_months=w["avg_tenure_months"],
        active_development_plans=0,
    )


@router.get("/ai/hiring-forecast")
async def hiring_forecast(
    planned_growth_percent: float = Query(default=10.0, ge=0, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(hr_staff),
):
    m = await get_org_metrics(db, user.organization_id)
    w = await _workforce(db, user.organization_id)
    return await predict_hiring_needs(
        current_headcount=m["headcount"],
        planned_growth_percent=planned_growth_percent,
        recent_attrition_rate=w["attrition_rate"],
        average_time_to_hire_days=m["avg_time_to_hire_days"] or 30.0,
    )
