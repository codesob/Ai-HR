"""What the HR agent can do.

Each tool is one real operation on the workspace. Tools are scoped to the agent's organization and to the
role it acts for. Consequential changes raise NeedsApproval: the runner turns them into a proposal that a
person approves in the app, and only then does the handler run again with ctx.approved set.
"""

import calendar
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.entities import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Interview,
    Job,
    OnboardingTask,
    User,
    UserRole,
)
from shared.models.leave import LeaveRequest, LeaveStatus, LeaveType
from shared.models.payroll import Payslip, SalaryProfile
from shared.services.nepal.calendar import BSMonth, last_completed_month, month_of
from shared.models.screening import Assessment, VideoScreen
from shared.services import handbook, hr_actions, screening
from shared.services.events import publish_notification
from shared.services.pii import mask_pii

STAFF = {UserRole.ADMIN, UserRole.RECRUITER}
ADMIN = {UserRole.ADMIN}
EVERYONE_STAFFED = {UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE}
ALL = {UserRole.ADMIN, UserRole.RECRUITER, UserRole.EMPLOYEE, UserRole.CANDIDATE}

# Stages the agent may set on its own; anything else waits for a person.
AUTO_STAGES = {ApplicationStatus.SCREENING, ApplicationStatus.ASSESSMENT}


class NeedsApproval(Exception):  # noqa: N818 - control flow, not an error
    def __init__(self, summary: str):
        super().__init__(summary)
        self.summary = summary


class ToolError(Exception):
    """A problem the model should read and recover from (bad id, not allowed …)."""


@dataclass
class Ctx:
    db: AsyncSession
    organization_id: int
    # The person the agent acts for; None on a scheduled run, which acts with HR-manager rights.
    user: User | None
    approved: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def role(self) -> UserRole:
        return self.user.role if self.user else UserRole.ADMIN


Handler = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    params: dict
    required: list[str]
    roles: set[UserRole]
    handler: Handler
    # Always needs a person's OK (the handler may also ask for it case by case).
    approval: bool = False

    def spec(self) -> dict:
        props = dict(self.params)
        required = list(self.required)
        if self.approval or self.name in CAN_ASK:
            props["reason"] = {"type": "string", "description": "One sentence a busy HR manager can check: why this action."}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }


REGISTRY: dict[str, Tool] = {}
# Tools that sometimes ask for approval, so the model should always give a reason.
CAN_ASK = {"move_candidate", "decide_leave"}


def tool(name: str, description: str, roles: set[UserRole], params: dict | None = None,
         required: list[str] | None = None, approval: bool = False):
    def register(fn: Handler) -> Handler:
        REGISTRY[name] = Tool(name, description, params or {}, required or [], roles, fn, approval)
        return fn
    return register


def tools_for(role: UserRole) -> list[Tool]:
    return [t for t in REGISTRY.values() if role in t.roles]


# ---------- helpers ----------

def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _application(ctx: Ctx, application_id: int) -> Application:
    app = (await ctx.db.execute(
        select(Application)
        .where(Application.id == application_id, Application.organization_id == ctx.organization_id)
        .options(selectinload(Application.candidate), selectinload(Application.job))
    )).scalar_one_or_none()
    if not app:
        raise ToolError(f"No application {application_id} in this workspace.")
    return app


def _month_bounds(month: str) -> tuple[date, date]:
    """First and last AD day of a month given as YYYY-MM: a Nepali (BS) month for years from 2070, else AD."""
    try:
        year, mon = (int(p) for p in month.split("-"))
        if year >= 2070:
            bs = BSMonth(year, mon)
            if not 1 <= mon <= 12:
                raise ValueError
            return bs.start, bs.end
        start = date(year, mon, 1)
    except ValueError:
        raise ToolError("month must look like 2083-06 (Nepali year and month)") from None
    return start, date(year, mon, calendar.monthrange(year, mon)[1])


def _month_label(month: str) -> str:
    year, mon = (int(p) for p in month.split("-"))
    return BSMonth(year, mon).label if year >= 2070 else date(year, mon, 1).strftime("%B %Y")


def _last_month() -> str:
    """The last Nepali month that has fully ended, as YYYY-MM in BS."""
    bs = last_completed_month(_today())
    return f"{bs.year}-{bs.month:02d}"


def _business_days_until(day: date) -> int:
    d, n = _today(), 0
    while d < day:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


# ---------- looking around ----------

@tool("get_workload", "Start here. What is waiting in the workspace right now: new applicants per open job, "
      "time-off requests waiting, interviews coming up, and whether last month's payroll has been run.", STAFF)
async def get_workload(ctx: Ctx) -> dict:
    db, org = ctx.db, ctx.organization_id
    jobs = (await db.execute(select(Job).where(Job.organization_id == org, Job.status == "open"))).scalars().all()
    waiting = dict((await db.execute(
        select(Application.job_id, func.count())
        .where(Application.organization_id == org, Application.status == ApplicationStatus.APPLIED)
        .group_by(Application.job_id)
    )).all())
    pending_leave = (await db.execute(
        select(func.count()).select_from(LeaveRequest)
        .where(LeaveRequest.organization_id == org, LeaveRequest.status == LeaveStatus.PENDING)
    )).scalar_one()
    upcoming = (await db.execute(
        select(func.count()).select_from(Interview)
        .where(Interview.organization_id == org, Interview.status == "scheduled",
               Interview.scheduled_at >= datetime.now(timezone.utc))
    )).scalar_one()
    month = _last_month()
    start, end = _month_bounds(month)
    salaried = (await db.execute(
        select(func.count()).select_from(SalaryProfile).join(User, User.id == SalaryProfile.user_id)
        .where(SalaryProfile.organization_id == org, User.is_active)
    )).scalar_one()
    paid = (await db.execute(
        select(func.count()).select_from(Payslip)
        .where(Payslip.organization_id == org, Payslip.period_start == start, Payslip.period_end == end)
    )).scalar_one()
    return {
        "today": _today().isoformat(),
        "open_jobs": [{"job_id": j.id, "title": j.title, "new_applicants": waiting.get(j.id, 0)} for j in jobs],
        "time_off_requests_waiting": pending_leave,
        "upcoming_interviews": upcoming,
        "payroll": {"month": month, "people_with_salary": salaried, "already_paid": paid},
    }


@tool("list_applicants", "Everyone who applied to a job, best match first, with their match score (0-100), "
      "matched and missing skills, and current stage.", STAFF,
      {"job_id": {"type": "integer"}, "stage": {"type": "string", "description": "Optional: only this stage, e.g. applied"}},
      ["job_id"])
async def list_applicants(ctx: Ctx, job_id: int, stage: str | None = None) -> dict:
    job = (await ctx.db.execute(
        select(Job).where(Job.id == job_id, Job.organization_id == ctx.organization_id)
    )).scalar_one_or_none()
    if not job:
        raise ToolError(f"No job {job_id} in this workspace.")
    q = (select(Application).where(Application.job_id == job_id, Application.organization_id == ctx.organization_id)
         .options(selectinload(Application.candidate)))
    if stage:
        q = q.where(Application.status == ApplicationStatus(stage))
    apps = (await ctx.db.execute(q.order_by(Application.rank_score.desc().nullslast()))).scalars().all()
    out = []
    for a in apps:
        exp = a.match_explanation or {}
        out.append({
            "application_id": a.id,
            "name": a.candidate.full_name if a.candidate else None,
            "email": a.candidate.email if a.candidate else None,
            "stage": a.status.value,
            "score": None if a.match_score is None else round(a.match_score * 100),
            "matched_skills": exp.get("matched_skills", []),
            "missing_skills": exp.get("missing_skills", []),
            "enough_experience": None if exp.get("experience_fit") is None else exp["experience_fit"] >= 1,
        })
    return {"job": {"title": job.title, "required_skills": job.required_skills,
                    "min_experience_years": job.min_experience_years}, "applicants": out}


@tool("list_time_off_requests", "Time-off requests waiting for a decision, with how many days each person has left "
      "and whether the request gives the notice the policy asks for (3 business days for annual leave).", ADMIN)
async def list_time_off_requests(ctx: Ctx) -> list[dict]:
    rows = (await ctx.db.execute(
        select(LeaveRequest, User).join(User, User.id == LeaveRequest.user_id)
        .where(LeaveRequest.organization_id == ctx.organization_id, LeaveRequest.status == LeaveStatus.PENDING)
        .order_by(LeaveRequest.start_date)
    )).all()
    out = []
    for leave, person in rows:
        allowed, used = await hr_actions.leave_allowance(ctx.db, person.id, leave.leave_type, leave.start_date.year)
        out.append({
            "leave_id": leave.id, "employee": person.full_name, "type": leave.leave_type.value,
            "start": leave.start_date.isoformat(), "end": leave.end_date.isoformat(),
            "days": hr_actions.leave_days(leave), "reason": leave.reason,
            "days_left_before_this": None if allowed is None else allowed - used,
            "business_days_notice": _business_days_until(leave.start_date),
        })
    return out


@tool("list_team", "Everyone in the workspace who isn't a job applicant: name, email, role, and yearly salary if set.", ADMIN)
async def list_team(ctx: Ctx) -> list[dict]:
    rows = (await ctx.db.execute(
        select(User, SalaryProfile.annual_base).outerjoin(SalaryProfile, SalaryProfile.user_id == User.id)
        .where(User.organization_id == ctx.organization_id, User.role != UserRole.CANDIDATE, User.is_active)
    )).all()
    return [{"name": u.full_name, "email": u.email, "role": u.role.value, "yearly_salary": s} for u, s in rows]


@tool("search_policies", "Look up the company's HR policies (leave, pay, benefits, remote work, hiring, onboarding). "
      "Use this before answering any policy question, and say which document the answer comes from. Write the "
      "query in English, even if the person asked in Nepali.", ALL,
      {"query": {"type": "string"}}, ["query"])
async def search_policies(ctx: Ctx, query: str) -> list[dict]:
    try:
        return await handbook.search(ctx.db, ctx.organization_id, query)
    except Exception:  # noqa: BLE001 - vector store down: say so instead of failing the run
        raise ToolError("The policy library isn't reachable right now.") from None


# ---------- hiring ----------

@tool("read_resume", "Read an applicant's resume: skills, years of experience, education, certifications, past "
      "roles, and the resume text itself (contact details removed). Use it before deciding on anyone.", STAFF,
      {"application_id": {"type": "integer"}}, ["application_id"])
async def read_resume(ctx: Ctx, application_id: int) -> dict:
    app = await _application(ctx, application_id)
    profile = (await ctx.db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == app.candidate_id)
    )).scalar_one_or_none()
    job = app.job
    base = {
        "application_id": application_id,
        "name": app.candidate.full_name if app.candidate else None,
        "job": {"title": job.title, "required_skills": job.required_skills,
                "min_experience_years": job.min_experience_years} if job else None,
    }
    if not profile or not (profile.resume_text or profile.parsed_data):
        return {**base, "resume": None, "note": "No resume uploaded yet."}
    parsed = dict(profile.parsed_data or {})
    for key in ("email", "phone", "name"):
        parsed.pop(key, None)
    text = profile.resume_text or ""
    return {
        **base,
        "skills": profile.skills,
        "experience_years": profile.experience_years,
        "education": profile.education,
        "details": mask_pii(parsed),
        "resume_text": mask_pii(text[:3500]) + ("…" if len(text) > 3500 else ""),
        **({"note": "Read from a photo or scan by a vision model: names, places and dates (especially in Nepali "
                    "script) may be misread. Don't reject on those details; check the original file."}
           if parsed.get("read_from_scan") else {}),
    }


@tool("move_candidate", "Move an application to another hiring stage. screening and assessment happen right away; "
      "interview should go through schedule_interview; offer, hired and rejected are sent to a person to approve.",
      STAFF,
      {"application_id": {"type": "integer"},
       "stage": {"type": "string", "enum": ["screening", "assessment", "offer", "hired", "rejected"]}},
      ["application_id", "stage"])
async def move_candidate(ctx: Ctx, application_id: int, stage: str) -> dict:
    app = await _application(ctx, application_id)
    new = ApplicationStatus(stage)
    name = app.candidate.full_name if app.candidate else "this candidate"
    job = app.job.title if app.job else "the job"
    if new not in AUTO_STAGES and not ctx.approved:
        verb = {"offer": "Make an offer to", "hired": "Mark as hired:", "rejected": "Reject"}.get(stage, f"Move to {stage}:")
        raise NeedsApproval(f"{verb} {name} ({job})")
    await hr_actions.set_application_status(ctx.db, ctx.organization_id, application_id, new)
    return {"application_id": application_id, "name": name, "stage": stage}


@tool("schedule_interview", "Book an interview for an application. Emails the candidate and the interviewer and moves "
      "the application to the interview stage. Use a weekday, 09:00-17:00 UTC, at least one business day ahead.",
      STAFF,
      {"application_id": {"type": "integer"},
       "start": {"type": "string", "description": "ISO date-time in UTC, e.g. 2026-11-03T14:00:00Z"},
       "interviewer_email": {"type": "string", "description": "Optional; defaults to the person you act for"},
       "duration_minutes": {"type": "integer", "description": "Default 45"}},
      ["application_id", "start"])
async def schedule_interview(ctx: Ctx, application_id: int, start: str, interviewer_email: str | None = None,
                             duration_minutes: int = 45) -> dict:
    app = await _application(ctx, application_id)
    try:
        when = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        raise ToolError("start must be an ISO date-time like 2026-11-03T14:00:00Z") from None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when <= datetime.now(timezone.utc):
        raise ToolError("That time is in the past.")
    if app.status in (ApplicationStatus.REJECTED, ApplicationStatus.HIRED):
        raise ToolError(f"This application is already {app.status.value}.")
    interviewer = interviewer_email or (ctx.user.email if ctx.user else None)
    if not interviewer:
        admin = (await ctx.db.execute(
            select(User).where(User.organization_id == ctx.organization_id, User.role == UserRole.ADMIN, User.is_active)
        )).scalars().first()
        interviewer = admin.email if admin else None
    if not interviewer:
        raise ToolError("No interviewer email; pass interviewer_email.")
    interview = await hr_actions.schedule_interview(
        ctx.db, ctx.organization_id, application_id, scheduled_at=when,
        interviewer_email=interviewer, duration_minutes=max(15, min(duration_minutes, 180)),
    )
    return {"interview_id": interview.id, "candidate": app.candidate.full_name if app.candidate else None,
            "at": when.isoformat(), "interviewer": interviewer}


# ---------- time off and pay ----------

@tool("decide_leave", "Approve or decline a time-off request. An approval that fits the policy (enough days left, "
      "3 business days' notice for annual leave) happens right away; anything else, and every decline, goes to a "
      "person to approve.", ADMIN,
      {"leave_id": {"type": "integer"}, "decision": {"type": "string", "enum": ["approve", "decline"]}},
      ["leave_id", "decision"])
async def decide_leave(ctx: Ctx, leave_id: int, decision: str) -> dict:
    leave = (await ctx.db.execute(
        select(LeaveRequest).where(LeaveRequest.id == leave_id, LeaveRequest.organization_id == ctx.organization_id)
    )).scalar_one_or_none()
    if not leave:
        raise ToolError(f"No time-off request {leave_id}.")
    if leave.status != LeaveStatus.PENDING:
        raise ToolError(f"That request was already {leave.status.value}.")
    person = await ctx.db.get(User, leave.user_id)
    who = person.full_name if person else "someone"
    days = hr_actions.leave_days(leave)
    label = f"{who}'s {leave.leave_type.value} leave, {leave.start_date:%b %d} – {leave.end_date:%b %d} ({days} days)"

    if decision == "decline":
        if not ctx.approved:
            raise NeedsApproval(f"Decline {label}")
        status = LeaveStatus.REJECTED
    else:
        if not ctx.approved:
            allowed, used = await hr_actions.leave_allowance(ctx.db, leave.user_id, leave.leave_type, leave.start_date.year)
            problems = []
            if allowed is not None and used + days > allowed:
                problems.append(f"only {allowed - used} days left")
            if leave.leave_type == LeaveType.ANNUAL and _business_days_until(leave.start_date) < 3:
                problems.append("less than 3 business days' notice")
            if leave.leave_type in (LeaveType.UNPAID, LeaveType.MATERNITY):
                problems.append(f"{leave.leave_type.value} leave always needs a person")
            if problems:
                raise NeedsApproval(f"Approve {label} ({'; '.join(problems)})")
        status = LeaveStatus.APPROVED
    reviewer = ctx.user.id if ctx.user else None
    try:
        await hr_actions.review_leave(ctx.db, ctx.organization_id, leave_id, status, reviewer)
    except PermissionError as exc:
        raise ToolError(str(exc)) from None
    return {"leave_id": leave_id, "employee": who, "status": status.value}


@tool("run_payroll", "Pay everyone with a salary for one month and create their payslips. Always sent to a person to "
      "approve first. People already paid for that month are skipped.", ADMIN,
      {"month": {"type": "string", "description": "Nepali (BS) month as YYYY-MM, e.g. 2083-06 for Asoj 2083; "
                 "usually the last month that has ended"}}, ["month"], approval=True)
async def run_payroll(ctx: Ctx, month: str) -> dict:
    start, end = _month_bounds(month)
    if end >= _today():
        raise ToolError("That month hasn't ended yet.")
    if not ctx.approved:
        bs = month_of(end)
        paid = set((await ctx.db.execute(
            select(Payslip.user_id).where(
                Payslip.organization_id == ctx.organization_id,
                (Payslip.period_start == start) & (Payslip.period_end == end)
                | (Payslip.bs_year == bs.year) & (Payslip.bs_month == bs.month))
        )).scalars())
        rows = [(uid, base) for uid, base in (await ctx.db.execute(
            select(SalaryProfile.user_id, SalaryProfile.annual_base).join(User, User.id == SalaryProfile.user_id)
            .where(SalaryProfile.organization_id == ctx.organization_id, User.is_active)
        )).all() if uid not in paid]
        if not rows:
            raise ToolError(f"Everyone with a salary is already paid for {_month_label(month)}.")
        gross = sum(base / 12 for _, base in rows)
        raise NeedsApproval(f"Run payroll for {_month_label(month)}: {len(rows)} people, "
                            f"about NPR {gross:,.0f} before SSF and tax")
    try:
        return await hr_actions.run_org_payroll(ctx.db, ctx.organization_id, start, end)
    except hr_actions.ConflictError as exc:
        raise ToolError(str(exc)) from None


@tool("send_message", "Email someone in this workspace (an employee, or a person who applied to one of its jobs) "
      "and post it to their in-app inbox. Keep it short and plain; sign off as 'HR'.", STAFF,
      {"to_email": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
      ["to_email", "subject", "body"])
async def send_message(ctx: Ctx, to_email: str, subject: str, body: str) -> dict:
    member = (await ctx.db.execute(
        select(User).where(func.lower(User.email) == to_email.strip().lower(), User.organization_id == ctx.organization_id)
    )).scalar_one_or_none()
    if not member:
        raise ToolError("You can only message people in this workspace.")
    note = await publish_notification(
        ctx.db, organization_id=ctx.organization_id, recipient=member.email, channel="email",
        subject=subject[:255], body=body[:4000], event_type="agent.message", send_now=True,
    )
    return {"to": member.email, "delivered": note.status == "sent"}


# ---------- screening: tasks and video ----------

@tool("send_task", "Send an applicant a take-home task with a deadline, by email and in their account. Write clear, "
      "fair instructions tied to the job's requirements, doable in 2-4 hours. Moves them to the assessment stage.",
      STAFF,
      {"application_id": {"type": "integer"}, "title": {"type": "string"},
       "instructions": {"type": "string"}, "due_days": {"type": "integer", "description": "Default 5"}},
      ["application_id", "title", "instructions"])
async def send_task(ctx: Ctx, application_id: int, title: str, instructions: str, due_days: int = 5) -> dict:
    try:
        task = await screening.send_assessment(ctx.db, ctx.organization_id, application_id, title=title,
                                               instructions=instructions, due_days=due_days)
    except (hr_actions.NotFoundError, screening.ScreeningError) as exc:
        raise ToolError(str(exc)) from None
    return {"task_id": task.id, "due": task.due_at.date().isoformat()}


@tool("send_video_screen", "Invite an applicant to record short video answers in their browser (English or Nepali). "
      "Leave questions empty for three sensible defaults, or give up to six of your own.", STAFF,
      {"application_id": {"type": "integer"}, "questions": {"type": "array", "items": {"type": "string"}},
       "due_days": {"type": "integer", "description": "Default 5"}},
      ["application_id"])
async def send_video_screen(ctx: Ctx, application_id: int, questions: list[str] | None = None, due_days: int = 5) -> dict:
    try:
        screen = await screening.invite_video_screen(ctx.db, ctx.organization_id, application_id,
                                                     questions=questions, due_days=due_days)
    except (hr_actions.NotFoundError, screening.ScreeningError) as exc:
        raise ToolError(str(exc)) from None
    return {"video_screen_id": screen.id, "questions": screen.questions}


@tool("list_screening_to_review", "Submitted tasks and finished video screens waiting for a pass/fail decision, "
      "with the AI's review of each.", STAFF)
async def list_screening_to_review(ctx: Ctx) -> list[dict]:
    out = []
    for model, kind, ready in ((Assessment, "task", "submitted"), (VideoScreen, "video", "completed")):
        rows = (await ctx.db.execute(
            select(model, Application).join(Application, Application.id == model.application_id)
            .where(model.organization_id == ctx.organization_id, model.status == ready)
            .options(selectinload(Application.candidate), selectinload(Application.job))
        )).all()
        out += [{"kind": kind, "id": item.id, "applicant": app.candidate.full_name, "job": app.job.title,
                 "ai_score": item.ai_score, "ai_recommendation": item.ai_recommendation or "not reviewed yet",
                 "ai_feedback": item.ai_feedback} for item, app in rows]
    return out


@tool("decide_screening", "Pass or fail a submitted task or video screen. Always goes to a person to confirm: the AI "
      "recommends, a human decides. Failing rejects the application.", STAFF,
      {"kind": {"type": "string", "enum": ["task", "video"]}, "id": {"type": "integer"},
       "decision": {"type": "string", "enum": ["pass", "fail"]}},
      ["kind", "id", "decision"], approval=True)
async def decide_screening(ctx: Ctx, kind: str, id: int, decision: str) -> dict:  # noqa: A002 - matches the tool schema
    model = Assessment if kind == "task" else VideoScreen
    item = (await ctx.db.execute(
        select(model, Application).join(Application, Application.id == model.application_id)
        .where(model.id == id, model.organization_id == ctx.organization_id)
        .options(selectinload(Application.candidate), selectinload(Application.job))
    )).first()
    if not item:
        raise ToolError(f"No {kind} {id}.")
    record, app = item
    if not ctx.approved:
        what = "task" if kind == "task" else "video answers"
        raise NeedsApproval(f"{decision.capitalize()} {app.candidate.full_name}'s {what} ({app.job.title})")
    try:
        await screening.decide(ctx.db, ctx.organization_id, "assessment" if kind == "task" else "video", id,
                               decision == "pass", ctx.user.id if ctx.user else None)
    except (hr_actions.NotFoundError, screening.ScreeningError) as exc:
        raise ToolError(str(exc)) from None
    return {"applicant": app.candidate.full_name, "decision": decision}


# ---------- onboarding ----------

@tool("list_onboarding", "New hires whose first-week checklist isn't finished, with each task and whether it's done.",
      STAFF)
async def list_onboarding(ctx: Ctx) -> list[dict]:
    rows = (await ctx.db.execute(
        select(OnboardingTask).where(
            OnboardingTask.organization_id == ctx.organization_id, OnboardingTask.status == "in_progress"
        ).order_by(OnboardingTask.created_at)
    )).scalars().all()
    return [{
        "onboarding_id": r.id, "name": r.employee_name, "email": r.employee_email, "role": r.role,
        "started": r.created_at.date().isoformat() if r.created_at else None,
        "tasks": [{"task_id": t["id"], "title": t["title"], "done": t["completed"]} for t in r.tasks],
    } for r in rows]


@tool("start_onboarding", "Open a first-week checklist for a new hire and send them a welcome email. "
      "Hiring someone through move_candidate does this automatically.", STAFF,
      {"name": {"type": "string"}, "email": {"type": "string"}, "role": {"type": "string"}},
      ["name", "email", "role"])
async def start_onboarding(ctx: Ctx, name: str, email: str, role: str) -> dict:
    if "@" not in email:
        raise ToolError("That doesn't look like an email address.")
    record, created = await hr_actions.start_onboarding(ctx.db, ctx.organization_id, name, email.strip(), role)
    return {"onboarding_id": record.id, "name": record.employee_name,
            "already_open": not created, "tasks": len(record.tasks)}


@tool("complete_onboarding_task", "Tick off a task on a new hire's checklist, once you know it's actually done.",
      STAFF, {"onboarding_id": {"type": "integer"}, "task_id": {"type": "string"}}, ["onboarding_id", "task_id"])
async def complete_onboarding_task(ctx: Ctx, onboarding_id: int, task_id: str) -> dict:
    try:
        record = await hr_actions.set_onboarding_task(ctx.db, ctx.organization_id, onboarding_id, task_id, True)
    except hr_actions.NotFoundError as exc:
        raise ToolError(str(exc)) from None
    title = next(t["title"] for t in record.tasks if t["id"] == task_id)
    left = sum(not t["completed"] for t in record.tasks)
    return {"name": record.employee_name, "task": title, "tasks_left": left}


# ---------- self-service (acts only for the signed-in person) ----------

def _me(ctx: Ctx) -> User:
    if not ctx.user:
        raise ToolError("Self-service tools need a signed-in person.")
    return ctx.user


@tool("my_time_off", "The signed-in person's own time-off requests and how many days they have left this year.",
      EVERYONE_STAFFED)
async def my_time_off(ctx: Ctx) -> dict:
    me = _me(ctx)
    year = _today().year
    left = {}
    for t in (LeaveType.ANNUAL, LeaveType.SICK):
        allowed, used = await hr_actions.leave_allowance(ctx.db, me.id, t, year)
        left[t.value] = None if allowed is None else allowed - used
    requests = (await ctx.db.execute(
        select(LeaveRequest).where(LeaveRequest.user_id == me.id).order_by(LeaveRequest.start_date.desc()).limit(10)
    )).scalars().all()
    return {"days_left_this_year": left, "requests": [
        {"type": r.leave_type.value, "start": r.start_date.isoformat(), "end": r.end_date.isoformat(),
         "status": r.status.value} for r in requests
    ]}


@tool("request_time_off", "Book time off for the signed-in person. Confirm the dates with them first if they were "
      "vague. HR is told and decides.", EVERYONE_STAFFED,
      {"leave_type": {"type": "string", "enum": ["annual", "sick", "unpaid", "maternity"]},
       "start_date": {"type": "string", "description": "YYYY-MM-DD"},
       "end_date": {"type": "string", "description": "YYYY-MM-DD"},
       "note": {"type": "string"}},
      ["leave_type", "start_date", "end_date"])
async def request_time_off(ctx: Ctx, leave_type: str, start_date: str, end_date: str, note: str = "") -> dict:
    me = _me(ctx)
    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except ValueError:
        raise ToolError("Dates must look like 2026-11-03.") from None
    if end < start:
        raise ToolError("The last day is before the first day.")
    if start < _today():
        raise ToolError("That date has already passed.")
    clash = (await ctx.db.execute(
        select(LeaveRequest).where(
            LeaveRequest.user_id == me.id, LeaveRequest.status != LeaveStatus.REJECTED,
            LeaveRequest.start_date <= end, LeaveRequest.end_date >= start,
        )
    )).scalars().first()
    if clash:
        raise ToolError(f"You already have time off booked from {clash.start_date} to {clash.end_date}.")
    leave = LeaveRequest(organization_id=ctx.organization_id, user_id=me.id, leave_type=LeaveType(leave_type),
                         start_date=start, end_date=end, reason=note[:1024])
    ctx.db.add(leave)
    await ctx.db.flush()
    return {"leave_id": leave.id, "status": "pending", "days": hr_actions.leave_days(leave)}


@tool("my_payslips", "The signed-in person's recent payslips.", EVERYONE_STAFFED)
async def my_payslips(ctx: Ctx) -> list[dict]:
    me = _me(ctx)
    slips = (await ctx.db.execute(
        select(Payslip).where(Payslip.user_id == me.id).order_by(Payslip.period_start.desc()).limit(6)
    )).scalars().all()
    return [{"month": p.period_start.strftime("%B %Y"), "gross": round(p.gross_amount, 2),
             "tax": round(p.tax_deduction, 2), "net": round(p.net_amount, 2)} for p in slips]


@tool("my_applications", "The signed-in job seeker's applications and what stage each one is at.", {UserRole.CANDIDATE})
async def my_applications(ctx: Ctx) -> list[dict]:
    me = _me(ctx)
    apps = (await ctx.db.execute(
        select(Application).where(Application.candidate_id == me.id).options(selectinload(Application.job))
    )).scalars().all()
    return [{"job": a.job.title if a.job else None, "stage": a.status.value} for a in apps]

