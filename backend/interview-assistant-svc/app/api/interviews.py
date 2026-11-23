from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.rbac import require_roles
from shared.core.config import get_settings
from shared.db.session import get_db
from shared.models.entities import Application, Interview, User, UserRole
from shared.schemas.common import InterviewCreate, InterviewOut
from shared.services import live_interview as live
from shared.services.hr_actions import NotFoundError
from shared.services.hr_actions import schedule_interview as schedule
from shared.services.uploads import read_limited

router = APIRouter(prefix="/interviews", tags=["interviews"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)
candidate_only = require_roles(UserRole.CANDIDATE)
in_the_call = require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.CANDIDATE)


class InterviewDetail(InterviewOut):
    """Everything the hiring team sees about one interview."""
    candidate_name: str | None = None
    job_title: str | None = None
    prep_questions: list[dict[str, Any]] = []
    recording_consent: bool | None = None
    recording_on: bool = False
    recorded_parts: int = 0
    transcript: list[dict[str, Any]] = []
    transcript_english: str | None = None
    summary: dict[str, Any] | None = None
    summary_status: str = ""
    scorecard: dict[str, Any] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class RoomOut(BaseModel):
    id: int
    role: str
    job_title: str
    candidate_name: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    backup_link: str | None
    recording_consent: bool | None
    recording_on: bool
    ice_servers: list[dict[str, Any]]
    cursor: int = 0
    prep_questions: list[dict[str, Any]] = []


class MyInterview(BaseModel):
    id: int
    job_title: str
    scheduled_at: datetime
    duration_minutes: int
    status: str


class SignalIn(BaseModel):
    kind: str = Field(max_length=16)
    data: dict[str, Any] = {}


class SignalsOut(BaseModel):
    messages: list[dict[str, Any]]
    cursor: int


class Consent(BaseModel):
    allowed: bool


class RecordingSwitch(BaseModel):
    on: bool


class Scorecard(BaseModel):
    rating: int = Field(ge=1, le=5)
    recommendation: str = Field(pattern="^(advance|unsure|decline)$")
    notes: str = Field(default="", max_length=8000)


def _fail(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


def _detail(seat: live.Seat) -> InterviewDetail:
    iv, app = seat.interview, seat.application
    return InterviewDetail(
        id=iv.id, application_id=iv.application_id, scheduled_at=iv.scheduled_at,
        duration_minutes=iv.duration_minutes, meeting_link=iv.meeting_link, interviewer_email=iv.interviewer_email,
        status=iv.status, candidate_name=app.candidate.full_name if app.candidate else None,
        job_title=app.job.title if app.job else None, prep_questions=iv.prep_questions or [],
        recording_consent=iv.recording_consent, recording_on=iv.recording_on,
        recorded_parts=len({p["part"] for p in iv.recording or []}), transcript=iv.transcript or [],
        transcript_english=iv.transcript_english, summary=iv.summary, summary_status=iv.summary_status,
        scorecard=iv.scorecard, started_at=iv.started_at, ended_at=iv.ended_at,
    )


def _room(seat: live.Seat, cursor: int = 0) -> RoomOut:
    iv, app = seat.interview, seat.application
    return RoomOut(
        id=iv.id, role=seat.role, job_title=app.job.title if app.job else "the role",
        candidate_name=app.candidate.full_name if app.candidate else "Applicant", scheduled_at=iv.scheduled_at,
        duration_minutes=iv.duration_minutes, status=iv.status, backup_link=iv.meeting_link,
        recording_consent=iv.recording_consent, recording_on=iv.recording_on, ice_servers=live.ice_servers(),
        cursor=cursor, prep_questions=(iv.prep_questions or []) if seat.role == "interviewer" else [],
    )


async def _staff_seat(db: AsyncSession, user: User, interview_id: int) -> live.Seat:
    s = await live.seat(db, user, interview_id)
    if s.role != "interviewer":
        raise NotFoundError("Interview not found")
    return s


# ---------- hiring team ----------

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
async def list_interviews(application_id: int | None = None, db: AsyncSession = Depends(get_db, scope="function"),
                          user: User = Depends(hr_staff)):
    query = select(Interview).where(Interview.organization_id == user.organization_id)
    if application_id is not None:
        query = query.where(Interview.application_id == application_id)
    return (await db.execute(query.order_by(Interview.scheduled_at))).scalars().all()


# ---------- applicants ----------

@router.get("/mine", response_model=list[MyInterview])
async def my_interviews(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(candidate_only)):
    rows = (await db.execute(
        select(Interview, Application).join(Application, Application.id == Interview.application_id)
        .where(Application.candidate_id == user.id).options(selectinload(Application.job))
        .order_by(Interview.scheduled_at)
    )).all()
    return [MyInterview(id=iv.id, job_title=app.job.title if app.job else "", scheduled_at=iv.scheduled_at,
                        duration_minutes=iv.duration_minutes, status=iv.status) for iv, app in rows]


@router.get("/{interview_id}", response_model=InterviewDetail)
async def interview_detail(interview_id: int, db: AsyncSession = Depends(get_db, scope="function"),
                           user: User = Depends(hr_staff)):
    try:
        return _detail(await _staff_seat(db, user, interview_id))
    except NotFoundError as exc:
        raise _fail(exc) from None


@router.post("/{interview_id}/prep", response_model=InterviewDetail)
async def prepare(interview_id: int, db: AsyncSession = Depends(get_db, scope="function"),
                  user: User = Depends(hr_staff)):
    try:
        await live.prepare_questions(db, user, interview_id)
        return _detail(await _staff_seat(db, user, interview_id))
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.put("/{interview_id}/scorecard", response_model=InterviewDetail)
async def scorecard(interview_id: int, payload: Scorecard, db: AsyncSession = Depends(get_db, scope="function"),
                    user: User = Depends(hr_staff)):
    try:
        await live.save_scorecard(db, user, interview_id, rating=payload.rating,
                                  recommendation=payload.recommendation, notes=payload.notes.strip())
        return _detail(await _staff_seat(db, user, interview_id))
    except NotFoundError as exc:
        raise _fail(exc) from None


# ---------- the call room (both sides) ----------

@router.post("/{interview_id}/room/join", response_model=RoomOut)
async def join_room(interview_id: int, db: AsyncSession = Depends(get_db, scope="function"),
                    user: User = Depends(in_the_call)):
    try:
        seat, cursor = await live.join(db, user, interview_id)
        return _room(seat, cursor)
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.post("/{interview_id}/room/signal", status_code=204)
async def post_signal(interview_id: int, payload: SignalIn, db: AsyncSession = Depends(get_db, scope="function"),
                      user: User = Depends(in_the_call)):
    try:
        await live.send_signal(db, user, interview_id, payload.kind, payload.data)
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.get("/{interview_id}/room/signal", response_model=SignalsOut)
async def get_signals(interview_id: int, after: int = 0, user: User = Depends(in_the_call)):
    """Long poll for the other side's call setup messages."""
    try:
        messages, cursor = await live.wait_signals(user, interview_id, after)
    except NotFoundError as exc:
        raise _fail(exc) from None
    return SignalsOut(messages=messages, cursor=cursor)


@router.post("/{interview_id}/room/consent", status_code=204)
async def consent(interview_id: int, payload: Consent, db: AsyncSession = Depends(get_db, scope="function"),
                  user: User = Depends(candidate_only)):
    try:
        await live.set_consent(db, user, interview_id, payload.allowed)
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.post("/{interview_id}/room/recording", status_code=204)
async def recording_switch(interview_id: int, payload: RecordingSwitch,
                           db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    try:
        await live.set_recording(db, user, interview_id, payload.on)
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.post("/{interview_id}/room/audio", status_code=204)
async def upload_audio(interview_id: int, file: UploadFile = File(...), part: int = Form(ge=0, le=500),
                       track: str = Form(pattern="^(interviewer|candidate)$"), offset: float = Form(ge=0, le=86400),
                       language: str = Form(default="", pattern="^(en|ne)?$"),
                       db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    data = await read_limited(file, get_settings().max_interview_audio_mb * 1024 * 1024)
    try:
        await live.save_part(db, user, interview_id, part=part, track=track, offset=offset,
                             language=language or None, data=data, content_type=file.content_type or "")
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None


@router.post("/{interview_id}/room/end", response_model=InterviewDetail)
async def end_call(interview_id: int, background: BackgroundTasks,
                   db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    try:
        iv = await live.finish(db, user, interview_id)
        seat = await _staff_seat(db, user, interview_id)
    except (NotFoundError, live.InterviewError) as exc:
        raise _fail(exc) from None
    if iv.summary_status == "processing":
        background.add_task(live.process_later, user.organization_id, iv.id)
    return _detail(seat)
