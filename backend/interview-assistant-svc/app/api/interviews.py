from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Interview, User, UserRole
from shared.schemas.common import InterviewCreate, InterviewOut
from shared.services.hr_actions import NotFoundError
from shared.services.hr_actions import schedule_interview as schedule

router = APIRouter(prefix="/interviews", tags=["interviews"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


@router.post("", response_model=InterviewOut, status_code=201)
async def schedule_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    try:
        return await schedule(
            db, user.organization_id, payload.application_id,
            scheduled_at=payload.scheduled_at, interviewer_email=payload.interviewer_email,
            duration_minutes=payload.duration_minutes, meeting_link=payload.meeting_link,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None


@router.get("", response_model=list[InterviewOut])
async def list_interviews(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    result = await db.execute(
        select(Interview).where(Interview.organization_id == user.organization_id).order_by(Interview.scheduled_at)
    )
    return result.scalars().all()
