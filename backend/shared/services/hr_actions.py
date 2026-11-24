"""Core HR operations.

API endpoints and the HR agent both call these, so a change the agent makes behaves exactly like the same
change made by a person in the app. Every function is scoped to one organization.
"""

import secrets
from datetime import date, datetime, timedelta, timezone

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
from shared.services.nepal import payroll as nepal_payroll
from shared.services.nepal.calendar import BSMonth, month_of
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
    room = f"{get_settings().frontend_url.rstrip('/')}/interview/{interview.id}"
    backup = f"\nIf the call won't connect, use this backup room: {meeting_link}" if meeting_link else ""
    for recipient, subject, extra in (
        (interviewer_email, f"Interview scheduled: {job_title}", "\n\nThe room has suggested questions ready, and "
         "if the applicant agrees to recording you'll get a transcript and notes afterwards."),
        (application.candidate.email, f"Your interview for {job_title}", "\n\nIt's a video call in your browser; "
         "sign in with your applicant account. Before you join you'll be asked whether the call may be recorded "
         "for the hiring team's notes. It's your choice and doesn't affect the decision."),
    ):
        await publish_notification(
            db,
            organization_id=organization_id,
            recipient=recipient,
            channel="email",
            subject=subject,
            body=f"Interview for {job_title} at {when} ({duration_minutes} min).\nJoin: {room}{backup}{extra}",
            event_type="interview.scheduled",
            payload={"application_id": application_id, "interview_id": interview.id},
            send_now=True,
        )
    await db.refresh(interview)
    return interview


def nepal_employee(profile: SalaryProfile) -> nepal_payroll.Employee:
    """Monthly pay split into basic (which SSF is charged on) and allowances; all basic if no split is set."""
    gross = profile.annual_base / 12
    basic = min(profile.basic_monthly or gross, gross)
    return nepal_payroll.Employee(
        basic_monthly=basic, allowances_monthly=gross - basic, ssf_enrolled=profile.ssf_enrolled,
        married=profile.married, female=profile.female, remote_category=profile.remote_category,
        cit_monthly=profile.cit_monthly or 0, life_insurance_annual=profile.life_insurance_annual or 0,
        health_insurance_annual=profile.health_insurance_annual or 0,
    )


async def _year_to_date(db: AsyncSession, user_id: int, month: BSMonth) -> nepal_payroll.YearToDate:
    slips = (await db.execute(
        select(Payslip).where(Payslip.user_id == user_id, Payslip.fiscal_year == month.fiscal_year,
                              Payslip.period_end < month.start)
    )).scalars().all()
    total = lambda key: sum((s.breakdown or {}).get(key, 0) for s in slips)  # noqa: E731
    return nepal_payroll.YearToDate(assessable=total("assessable_this_month"),
                                    retirement=total("retirement_this_month"), tds=total("tds"), sst=total("sst"))


def _months_served(joined_on: date | None, month: BSMonth) -> int:
    if joined_on is None:
        return 12
    return max(0, (month.end.year - joined_on.year) * 12 + month.end.month - joined_on.month)


async def issue_payslip(
    db: AsyncSession, profile: SalaryProfile, period_start: date, period_end: date, festival: bool = False
) -> Payslip:
    """Work out one person's Nepal payslip for the BS month the period ends in (not yet flushed)."""
    month = month_of(period_end)
    emp = nepal_employee(profile)
    extra = nepal_payroll.festival_allowance(emp.basic_monthly, _months_served(profile.joined_on, month)) if festival else 0
    b = nepal_payroll.payslip(emp, month, await _year_to_date(db, profile.user_id, month), festival_allowance=extra)
    slip = Payslip(
        organization_id=profile.organization_id, user_id=profile.user_id,
        period_start=period_start, period_end=period_end,
        gross_amount=b["gross"], tax_deduction=b["tds"], net_amount=b["net"],
        fiscal_year=month.fiscal_year, bs_year=month.year, bs_month=month.month,
        ssf_employee=b["ssf_employee"], ssf_employer=b["ssf_employer"], breakdown=b,
    )
    db.add(slip)
    return slip


async def run_org_payroll(
    db: AsyncSession, organization_id: int, period_start: date, period_end: date, festival: bool = False
) -> dict:
    """Issue payslips for every active person with a salary; anyone already paid for the period is skipped."""
    month = month_of(period_end)
    profiles = (await db.execute(
        select(SalaryProfile)
        .join(User, User.id == SalaryProfile.user_id)
        .where(SalaryProfile.organization_id == organization_id, User.is_active)
    )).scalars().all()
    already_paid = set((await db.execute(
        select(Payslip.user_id).where(
            Payslip.organization_id == organization_id,
            (Payslip.period_start == period_start) & (Payslip.period_end == period_end)
            | (Payslip.bs_year == month.year) & (Payslip.bs_month == month.month),
        )
    )).scalars())

    processed, total_net = 0, 0.0
    for profile in profiles:
        if profile.user_id in already_paid:
            continue
        slip = await issue_payslip(db, profile, period_start, period_end, festival)
        processed += 1
        total_net += slip.net_amount
    try:
        await db.flush()
    except IntegrityError:
        raise ConflictError("Payroll is already running for this period") from None
    return {"processed": processed, "skipped": len(already_paid), "total_net": round(total_net, 2),
            "bs_month": month.label, "fiscal_year": month.fiscal_year}


async def remittance(db: AsyncSession, organization_id: int, month: BSMonth) -> dict:
    """What the employer owes SSF and IRD for one BS month, per person and in total, with due dates."""
    rows = (await db.execute(
        select(Payslip, User, SalaryProfile)
        .join(User, User.id == Payslip.user_id)
        .outerjoin(SalaryProfile, SalaryProfile.user_id == Payslip.user_id)
        .where(Payslip.organization_id == organization_id, Payslip.bs_year == month.year,
               Payslip.bs_month == month.month)
        .order_by(User.full_name)
    )).all()
    people = [{
        "user_id": user.id, "full_name": user.full_name,
        "pan": profile.pan if profile else None, "ssf_number": profile.ssf_number if profile else None,
        "basic": slip.breakdown.get("basic", 0), "gross": slip.gross_amount,
        "ssf_employee": slip.ssf_employee, "ssf_employer": slip.ssf_employer,
        "ssf_total": round(slip.ssf_employee + slip.ssf_employer, 2),
        "sst": slip.breakdown.get("sst", 0), "income_tax": slip.breakdown.get("income_tax", 0),
        "tds": slip.tax_deduction, "net": slip.net_amount,
    } for slip, user, profile in rows]
    total = lambda key: round(sum(p[key] for p in people), 2)  # noqa: E731
    after = month.end
    return {
        "bs_month": month.label, "fiscal_year": month.fiscal_year,
        "period_start": month.start, "period_end": month.end,
        "people": people,
        "ssf": {"employee": total("ssf_employee"), "employer": total("ssf_employer"), "total": total("ssf_total"),
                # Sources disagree on 15 vs 25 days; the earlier date is the safe one.
                "due": after + timedelta(days=15)},
        "ird": {"sst_11211": total("sst"), "income_tax": total("income_tax"), "total": total("tds"),
                "due": after + timedelta(days=25)},
        "missing_pan": [p["full_name"] for p in people if not p["pan"]],
        "missing_ssf_number": [p["full_name"] for p in people if p["ssf_employee"] and not p["ssf_number"]],
    }


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
