"""Core HR operations.

API endpoints and the HR agent both call these, so a change the agent makes behaves exactly like the same
change made by a person in the app. Every function is scoped to one organization.
"""

import secrets
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.config import get_settings
from shared.models.entities import Application, ApplicationStatus, Interview, OnboardingTask, User
from shared.models.leave import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from shared.models.payroll import Payslip, SalaryProfile
from shared.services.candidate_emails import company_name, email_applicant, stage_message
from shared.services.events import publish_notification
from shared.services.onboarding import create_onboarding_plan


class NotFoundError(LookupError):
    """The record doesn't exist in this organization."""


class ConflictError(RuntimeError):
    """The change clashes with another one already in progress."""


async def set_application_status(
    db: AsyncSession, organization_id: int, application_id: int, status: ApplicationStatus
) -> Application:
    app = (await db.execute(
        select(Application)
        .where(Application.id == application_id, Application.organization_id == organization_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found")
    changed = app.status != status
    app.status = status
    app.hired_at = datetime.now(timezone.utc) if status == ApplicationStatus.HIRED else None
    await db.flush()
    if changed and app.candidate:
        message = stage_message(status.value, app.candidate.full_name, app.job.title if app.job else "the role",
                                await company_name(db, organization_id))
        if message:
            await email_applicant(db, organization_id, app.candidate.email, *message,
                                  event_type=f"application.{status.value}", payload={"application_id": app.id})
    if status == ApplicationStatus.HIRED and app.candidate:
        await start_onboarding(
            db, organization_id, app.candidate.full_name, app.candidate.email, app.job.title if app.job else "New hire"
        )
    return app


async def schedule_interview(
    db: AsyncSession,
    organization_id: int,
    application_id: int,
    *,
    scheduled_at: datetime,
    interviewer_email: str,
    duration_minutes: int = 60,
    meeting_link: str | None = None,
) -> Interview:
    """Books the interview, moves the application to the interview stage and emails both sides."""
    application = (await db.execute(
        select(Application)
        .where(Application.id == application_id, Application.organization_id == organization_id)
        .options(selectinload(Application.candidate), selectinload(Application.job))
    )).scalar_one_or_none()
    if not application:
        raise NotFoundError("Application not found")

    if not meeting_link:
        # A private video room nobody can guess; free, nothing to install.
        meeting_link = f"{get_settings().meeting_base_url.rstrip('/')}/aihr-{secrets.token_urlsafe(12)}"
    interview = Interview(
        organization_id=organization_id,
        application_id=application_id,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        interviewer_email=interviewer_email,
        meeting_link=meeting_link,
        status="scheduled",
    )
    application.status = ApplicationStatus.INTERVIEW
    db.add(interview)
    await db.flush()

    when = scheduled_at.strftime("%Y-%m-%d %H:%M %Z").strip()
    job_title = application.job.title if application.job else "the role"
    link = f"\nJoin: {meeting_link}" if meeting_link else ""
    for recipient, subject in (
        (interviewer_email, f"Interview scheduled: {job_title}"),
        (application.candidate.email, f"Your interview for {job_title}"),
    ):
        await publish_notification(
            db,
            organization_id=organization_id,
            recipient=recipient,
            channel="email",
            subject=subject,
            body=f"Interview for {job_title} at {when} ({duration_minutes} min).{link}",
            event_type="interview.scheduled",
            payload={"application_id": application_id, "interview_id": interview.id},
            send_now=True,
        )
    await db.refresh(interview)
    return interview


def calculate_net_salary(annual_base: float) -> tuple[float, float, float]:
    """Monthly gross, tax and net for a yearly salary (simple progressive brackets)."""
    gross_monthly = annual_base / 12
    if gross_monthly < 3000:
        tax_rate = 0.1
    elif gross_monthly < 7000:
        tax_rate = 0.2
    else:
        tax_rate = 0.3
    tax_deduction = gross_monthly * tax_rate
    return gross_monthly, tax_deduction, gross_monthly - tax_deduction


async def run_org_payroll(db: AsyncSession, organization_id: int, period_start: date, period_end: date) -> dict:
    """Issue payslips for every active person with a salary; anyone already paid for the period is skipped."""
    profiles = (await db.execute(
        select(SalaryProfile)
        .join(User, User.id == SalaryProfile.user_id)
        .where(SalaryProfile.organization_id == organization_id, User.is_active)
    )).scalars().all()
    already_paid = set((await db.execute(
        select(Payslip.user_id).where(
            Payslip.organization_id == organization_id,
            Payslip.period_start == period_start,
            Payslip.period_end == period_end,
        )
    )).scalars())

    processed, total_net = 0, 0.0
    for profile in profiles:
        if profile.user_id in already_paid:
            continue
        gross, tax, net = calculate_net_salary(profile.annual_base)
        db.add(Payslip(
            organization_id=organization_id, user_id=profile.user_id,
            period_start=period_start, period_end=period_end,
            gross_amount=gross, tax_deduction=tax, net_amount=net,
        ))
        processed += 1
        total_net += net
    try:
        await db.flush()
    except IntegrityError:
        raise ConflictError("Payroll is already running for this period") from None
    return {"processed": processed, "skipped": len(already_paid), "total_net": round(total_net, 2)}


def leave_days(leave: LeaveRequest) -> int:
    return (leave.end_date - leave.start_date).days + 1


async def leave_allowance(db: AsyncSession, user_id: int, leave_type: LeaveType, year: int) -> tuple[int | None, int]:
    """(days allowed per year or None if unlimited/unpaid, days already approved this year) for one leave type."""
    balance = (await db.execute(select(LeaveBalance).where(LeaveBalance.user_id == user_id))).scalar_one_or_none()
    allowed = {
        LeaveType.ANNUAL: balance.annual_days if balance else 20,
        LeaveType.SICK: balance.sick_days if balance else 10,
    }.get(leave_type)
    approved = (await db.execute(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user_id,
            LeaveRequest.leave_type == leave_type,
            LeaveRequest.status == LeaveStatus.APPROVED,
            func.extract("year", LeaveRequest.start_date) == year,
        )
    )).scalars().all()
    return allowed, sum(leave_days(lv) for lv in approved)


async def review_leave(
    db: AsyncSession, organization_id: int, leave_id: int, status: LeaveStatus, reviewer_id: int | None
) -> LeaveRequest:
    leave = (await db.execute(
        select(LeaveRequest).where(LeaveRequest.id == leave_id, LeaveRequest.organization_id == organization_id)
    )).scalar_one_or_none()
    if not leave:
        raise NotFoundError("Leave request not found")
    if reviewer_id is not None and leave.user_id == reviewer_id:
        raise PermissionError("You cannot approve your own leave")
    leave.status = status
    leave.reviewed_by_id = reviewer_id
    await db.flush()

    employee = await db.get(User, leave.user_id)
    if employee:
        verdict = "approved" if status == LeaveStatus.APPROVED else "declined"
        await publish_notification(
            db,
            organization_id=organization_id,
            recipient=employee.email,
            subject=f"Your time off was {verdict}",
            body=f"Your {leave.leave_type.value} leave from {leave.start_date} to {leave.end_date} was {verdict}.",
            event_type="leave.reviewed",
            payload={"leave_id": leave.id, "status": status.value},
        )
    return leave


async def start_onboarding(
    db: AsyncSession, organization_id: int, name: str, email: str, role: str
) -> tuple[OnboardingTask, bool]:
    """Opens a first-week checklist and sends a welcome email. (record, created); one open checklist per person."""
    existing = (await db.execute(
        select(OnboardingTask).where(
            OnboardingTask.organization_id == organization_id,
            func.lower(OnboardingTask.employee_email) == email.lower(),
            OnboardingTask.status == "in_progress",
        )
    )).scalars().first()
    if existing:
        return existing, False
    record = OnboardingTask(
        organization_id=organization_id, employee_name=name, employee_email=email, role=role,
        tasks=create_onboarding_plan(name, role), status="in_progress",
    )
    db.add(record)
    await db.flush()
    steps = "\n".join(f"- {t['title']}" for t in record.tasks)
    first_name = name.split()[0] if name.strip() else "there"
    await publish_notification(
        db, organization_id=organization_id, recipient=email, channel="email",
        subject=f"Welcome aboard, {first_name}",
        body=f"Hi {first_name},\n\nWelcome to the team as {role}! Here's what we'll get done in your first week:\n\n"
             f"{steps}\n\nWe'll check in as each one is done. Reply any time with questions.\n\nHR",
        event_type="onboarding.started", payload={"onboarding_id": record.id}, send_now=True,
    )
    await db.refresh(record)
    return record, True


async def set_onboarding_task(
    db: AsyncSession, organization_id: int, onboarding_id: int, task_id: str, completed: bool
) -> OnboardingTask:
    record = (await db.execute(
        select(OnboardingTask).where(OnboardingTask.id == onboarding_id, OnboardingTask.organization_id == organization_id)
    )).scalar_one_or_none()
    if not record:
        raise NotFoundError("Onboarding not found")
    if not any(t["id"] == task_id for t in record.tasks):
        raise NotFoundError("No such task on this checklist")
    # A new list, so SQLAlchemy sees the JSON change.
    record.tasks = [{**t, "completed": completed} if t["id"] == task_id else t for t in record.tasks]
    record.status = "completed" if all(t["completed"] for t in record.tasks) else "in_progress"
    await db.flush()
    return record
