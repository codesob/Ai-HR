from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Application, ApplicationStatus, Interview, User, UserRole
from shared.schemas.common import InterviewCreate, InterviewOut
from shared.services.events import publish_notification

router = APIRouter(prefix="/interviews", tags=["interviews"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


@router.post("", response_model=InterviewOut, status_code=201)
async def schedule_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(hr_staff),
):
    application = (await db.execute(
        select(Application)
        .where(Application.id == payload.application_id, Application.organization_id == user.organization_id)
        .options(selectinload(Application.candidate), selectinload(Application.job))
    )).scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    interview = Interview(
        organization_id=user.organization_id,
        application_id=payload.application_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        interviewer_email=payload.interviewer_email,
        meeting_link=payload.meeting_link,
        status="scheduled",
    )
    application.status = ApplicationStatus.INTERVIEW
    db.add(interview)
    await db.flush()

    when = payload.scheduled_at.strftime("%Y-%m-%d %H:%M %Z").strip()
    job_title = application.job.title if application.job else "the role"
    link = f"\nJoin: {payload.meeting_link}" if payload.meeting_link else ""
    for recipient, subject in (
        (payload.interviewer_email, f"Interview scheduled: {job_title}"),
        (application.candidate.email, f"Your interview for {job_title}"),
    ):
        await publish_notification(
            db,
            organization_id=user.organization_id,
            recipient=recipient,
            channel="email",
            subject=subject,
            body=f"Interview for {job_title} at {when} ({payload.duration_minutes} min).{link}",
            event_type="interview.scheduled",
            payload={"application_id": payload.application_id, "interview_id": interview.id},
            send_now=True,
        )
    await db.refresh(interview)
    return interview


@router.get("", response_model=list[InterviewOut])
async def list_interviews(db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    result = await db.execute(
        select(Interview).where(Interview.organization_id == user.organization_id).order_by(Interview.scheduled_at)
    )
    return result.scalars().all()
