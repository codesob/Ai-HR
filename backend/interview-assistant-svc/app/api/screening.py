from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.rbac import require_roles
from shared.core.config import get_settings
from shared.db.session import get_db
from shared.models.entities import Application, User, UserRole
from shared.models.screening import Assessment, VideoScreen
from shared.services import screening
from shared.services.hr_actions import NotFoundError
from shared.services.storage import read_file
from shared.services.uploads import read_limited

router = APIRouter(prefix="/screening", tags=["screening"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)
candidate_only = require_roles(UserRole.CANDIDATE)


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    instructions: str = Field(min_length=10, max_length=8000)
    due_days: int = Field(default=5, ge=1, le=30)


class VideoScreenCreate(BaseModel):
    questions: list[str] = Field(default_factory=list, max_length=6)
    due_days: int = Field(default=5, ge=1, le=30)


class Submission(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class Decision(BaseModel):
    passed: bool


class AssessmentOut(BaseModel):
    id: int
    application_id: int
    title: str
    instructions: str
    due_at: datetime
    status: str
    submission: str
    submitted_at: datetime | None
    ai_score: int | None
    ai_recommendation: str
    ai_feedback: str
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class AnswerOut(BaseModel):
    index: int
    transcript: str | None
    english: str | None = None


class VideoScreenOut(BaseModel):
    id: int
    application_id: int
    questions: list[str]
    answers: list[AnswerOut]
    due_at: datetime
    status: str
    completed_at: datetime | None
    ai_score: int | None
    ai_recommendation: str
    ai_feedback: str
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class ApplicantAssessment(BaseModel):
    """What the applicant sees: no AI notes or internal review details."""
    id: int
    job_title: str
    title: str
    instructions: str
    due_at: datetime
    status: str
    submission: str


class ApplicantVideoScreen(BaseModel):
    id: int
    job_title: str
    questions: list[str]
    answered: list[int]
    due_at: datetime
    status: str


class ScreeningOut(BaseModel):
    assessments: list[AssessmentOut]
    video_screens: list[VideoScreenOut]


class MyScreening(BaseModel):
    assessments: list[ApplicantAssessment]
    video_screens: list[ApplicantVideoScreen]


def _fail(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


# ---------- hiring team ----------

@router.get("/applications/{application_id}", response_model=ScreeningOut)
async def for_application(application_id: int, db: AsyncSession = Depends(get_db, scope="function"),
                          user: User = Depends(hr_staff)):
    org = user.organization_id
    tasks = (await db.execute(select(Assessment).where(
        Assessment.application_id == application_id, Assessment.organization_id == org).order_by(Assessment.id))).scalars()
    screens = (await db.execute(select(VideoScreen).where(
        VideoScreen.application_id == application_id, VideoScreen.organization_id == org).order_by(VideoScreen.id))).scalars()
    return ScreeningOut(assessments=list(tasks), video_screens=list(screens))


@router.post("/applications/{application_id}/assessment", response_model=AssessmentOut, status_code=201)
async def send_task(application_id: int, payload: AssessmentCreate,
                    db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    try:
        return await screening.send_assessment(db, user.organization_id, application_id, title=payload.title,
                                               instructions=payload.instructions, due_days=payload.due_days)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None


@router.post("/applications/{application_id}/video", response_model=VideoScreenOut, status_code=201)
async def send_video_screen(application_id: int, payload: VideoScreenCreate,
                            db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    try:
        return await screening.invite_video_screen(db, user.organization_id, application_id,
                                                   questions=payload.questions, due_days=payload.due_days)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None


@router.post("/assessments/{item_id}/decision", response_model=AssessmentOut)
async def decide_task(item_id: int, payload: Decision, db: AsyncSession = Depends(get_db, scope="function"),
                      user: User = Depends(hr_staff)):
    try:
        return await screening.decide(db, user.organization_id, "assessment", item_id, payload.passed, user.id)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None


@router.post("/video/{item_id}/decision", response_model=VideoScreenOut)
async def decide_video(item_id: int, payload: Decision, db: AsyncSession = Depends(get_db, scope="function"),
                       user: User = Depends(hr_staff)):
    try:
        return await screening.decide(db, user.organization_id, "video", item_id, payload.passed, user.id)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None


@router.get("/video/{item_id}/answers/{index}")
async def watch_answer(item_id: int, index: int, db: AsyncSession = Depends(get_db, scope="function"),
                       user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER, UserRole.CANDIDATE))):
    """The recording itself, for the hiring team or the applicant who made it."""
    screen = (await db.execute(
        select(VideoScreen).join(Application, Application.id == VideoScreen.application_id)
        .where(VideoScreen.id == item_id, VideoScreen.organization_id == user.organization_id)
        .where(Application.candidate_id == user.id if user.role == UserRole.CANDIDATE else True)
    )).scalar_one_or_none()
    answer = next((a for a in (screen.answers if screen else []) if a["index"] == index), None)
    if not answer:
        raise HTTPException(status_code=404, detail="Recording not found")
    data = await read_file(answer["file"])
    return Response(content=data, media_type=answer["content_type"], headers={"Cache-Control": "private, max-age=300"})


# ---------- applicants ----------

@router.get("/mine", response_model=MyScreening)
async def mine(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(candidate_only)):
    apps = {a.id: a for a in (await db.execute(
        select(Application).where(Application.candidate_id == user.id).options(selectinload(Application.job))
    )).scalars()}
    tasks = (await db.execute(select(Assessment).where(Assessment.application_id.in_(apps)).order_by(Assessment.id))).scalars()
    screens = (await db.execute(select(VideoScreen).where(VideoScreen.application_id.in_(apps)).order_by(VideoScreen.id))).scalars()
    return MyScreening(
        assessments=[ApplicantAssessment(
            id=t.id, job_title=apps[t.application_id].job.title, title=t.title, instructions=t.instructions,
            due_at=t.due_at, status=t.status if t.status in ("sent", "submitted") else "reviewed", submission=t.submission,
        ) for t in tasks],
        video_screens=[ApplicantVideoScreen(
            id=s.id, job_title=apps[s.application_id].job.title, questions=s.questions,
            answered=[a["index"] for a in s.answers], due_at=s.due_at,
            status=s.status if s.status in ("invited", "completed") else "reviewed",
        ) for s in screens],
    )


@router.post("/assessments/{item_id}/submit", status_code=204)
async def submit_task(item_id: int, payload: Submission, background: BackgroundTasks,
                      db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(candidate_only)):
    try:
        task = await screening.submit_assessment(db, user, item_id, payload.text)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None
    background.add_task(screening.review_assessment_later, user.organization_id, task.id)


@router.post("/video/{item_id}/answers/{index}", status_code=204)
async def record_answer(item_id: int, index: int, file: UploadFile = File(...),
                        language: str = Form(default="", pattern="^(en|ne)?$"),
                        db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(candidate_only)):
    data = await read_limited(file, get_settings().max_video_mb * 1024 * 1024)
    try:
        await screening.save_answer(db, user, item_id, index, data, file.content_type or "", language or None)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None


@router.post("/video/{item_id}/complete", status_code=204)
async def finish_screen(item_id: int, background: BackgroundTasks,
                        db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(candidate_only)):
    try:
        screen = await screening.complete_screen(db, user, item_id)
    except (NotFoundError, screening.ScreeningError) as exc:
        raise _fail(exc) from None
    background.add_task(screening.review_screen_later, user.organization_id, screen.id)
