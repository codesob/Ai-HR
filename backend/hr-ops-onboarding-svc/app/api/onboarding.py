from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import OnboardingTask, User, UserRole
from shared.schemas.common import OnboardingCreate, OnboardingOut
from shared.services.hr_actions import NotFoundError, set_onboarding_task, start_onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


class TaskUpdate(BaseModel):
    completed: bool


@router.post("", response_model=OnboardingOut, status_code=201)
async def start(
    payload: OnboardingCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    record, _ = await start_onboarding(
        db, user.organization_id, payload.employee_name, str(payload.employee_email), payload.role
    )
    return record


@router.get("", response_model=list[OnboardingOut])
async def list_onboarding(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    result = await db.execute(
        select(OnboardingTask)
        .where(OnboardingTask.organization_id == user.organization_id)
        .order_by(OnboardingTask.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{onboarding_id}/tasks/{task_id}", response_model=OnboardingOut)
async def update_task(
    onboarding_id: int,
    task_id: str,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    try:
        return await set_onboarding_task(db, user.organization_id, onboarding_id, task_id, payload.completed)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
