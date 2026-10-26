from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import OnboardingTask, User, UserRole
from shared.schemas.common import OnboardingCreate, OnboardingOut
from shared.services.onboarding import create_onboarding_plan

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


@router.post("", response_model=OnboardingOut, status_code=201)
async def start_onboarding(
    payload: OnboardingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(hr_staff),
):
    record = OnboardingTask(
        organization_id=user.organization_id,
        employee_name=payload.employee_name,
        employee_email=payload.employee_email,
        role=payload.role,
        tasks=create_onboarding_plan(payload.employee_name, payload.role),
        status="in_progress",
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("", response_model=list[OnboardingOut])
async def list_onboarding(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    result = await db.execute(
        select(OnboardingTask)
        .where(OnboardingTask.organization_id == user.organization_id)
        .order_by(OnboardingTask.created_at.desc())
    )
    return result.scalars().all()
