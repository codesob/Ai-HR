from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Application, ApplicationStatus, Interview, User, UserRole
from shared.schemas.common import InterviewCreate, InterviewOut
from shared.services.events import publish_notification

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewOut)
async def schedule_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    app_result = await db.execute(
        select(Application).where(Application.id == payload.application_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    interview = Interview(
        application_id=payload.application_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        interviewer_email=payload.interviewer_email,
        meeting_link=payload.meeting_link or f"https://meet.example.com/{payload.application_id}",
        status="scheduled",
    )
    application.status = ApplicationStatus.INTERVIEW
    db.add(interview)
    await db.flush()
    await publish_notification(
        db,
        recipient=payload.interviewer_email,
        subject="Interview scheduled",
        body=f"Interview for application #{payload.application_id} is scheduled.",
        event_type="interview.scheduled",
        payload={"application_id": payload.application_id, "interview_id": interview.id},
    )
    await db.refresh(interview)
    return interview


@router.get("", response_model=list[InterviewOut])
async def list_interviews(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    result = await db.execute(select(Interview).order_by(Interview.scheduled_at))
    return result.scalars().all()
