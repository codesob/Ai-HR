"""Take-home tasks and one-way video screens: sending them, receiving answers, AI review, and the human decision.

Both the API and the HR agent call these. The AI only recommends; pass/fail is always a person's call.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.config import get_settings
from shared.db.session import AsyncSessionLocal
from shared.models.entities import Application, ApplicationStatus, User
from shared.models.screening import Assessment, VideoScreen
from shared.services import hr_actions, screening_ai
from shared.services.candidate_emails import company_name, email_applicant, email_hiring_team, first_name
from shared.services.storage import read_file, store_file

logger = logging.getLogger(__name__)

VIDEO_TYPES = {"video/webm": ".webm", "video/mp4": ".mp4", "video/quicktime": ".mov"}


class ScreeningError(ValueError):
    """The request doesn't make sense in the current state (already submitted, wrong person …)."""


def default_questions(job_title: str) -> list[str]:
    return [
        f"Tell us briefly about yourself and why the {job_title} role interests you.",
        "Describe a piece of work you're proud of that's relevant to this job. What exactly was your part?",
        "Tell us about a time something went wrong at work or in a project. What did you do about it?",
    ]


def _links() -> tuple[str, str]:
    base = get_settings().frontend_url.rstrip("/")
    return f"{base}/candidate", f"{base}/recruiter"


async def _application(db: AsyncSession, organization_id: int, application_id: int) -> Application:
    app = (await db.execute(
        select(Application).where(Application.id == application_id, Application.organization_id == organization_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )).scalar_one_or_none()
    if not app:
        raise hr_actions.NotFoundError("Application not found")
    if app.status in (ApplicationStatus.HIRED, ApplicationStatus.REJECTED):
        raise ScreeningError(f"This application is already {app.status.value}.")
    return app


def _due(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 30)))


# ---------- tasks ----------

async def send_assessment(db: AsyncSession, organization_id: int, application_id: int, *, title: str,
                          instructions: str, due_days: int = 5) -> Assessment:
    app = await _application(db, organization_id, application_id)
    task = Assessment(organization_id=organization_id, application_id=app.id, title=title[:255],
                      instructions=instructions, due_at=_due(due_days))
    db.add(task)
    await hr_actions.set_application_status(db, organization_id, app.id, ApplicationStatus.ASSESSMENT)
    await db.flush()
    account, _ = _links()
    company = await company_name(db, organization_id)
    await email_applicant(
        db, organization_id, app.candidate.email, f"Your next step for {app.job.title}: {title}",
        f"Hi {first_name(app.candidate.full_name)},\n\nAs the next step for {app.job.title}, please complete this "
        f"task by {task.due_at:%A %d %B}.\n\n{title}\n\n{instructions}\n\nSubmit your answer here: {account}\n\n{company}",
        "assessment.sent", {"assessment_id": task.id},
    )
    return task


async def submit_assessment(db: AsyncSession, user: User, assessment_id: int, text: str) -> Assessment:
    task = (await db.execute(
        select(Assessment).join(Application, Application.id == Assessment.application_id)
        .where(Assessment.id == assessment_id, Application.candidate_id == user.id)
    )).scalar_one_or_none()
    if not task:
        raise hr_actions.NotFoundError("Task not found")
    if task.status != "sent":
        raise ScreeningError("You've already submitted this task.")
    if not text.strip():
        raise ScreeningError("Your answer is empty.")
    task.submission, task.status, task.submitted_at = text.strip(), "submitted", datetime.now(timezone.utc)
    await db.flush()
    return task


async def review_assessment_later(organization_id: int, assessment_id: int) -> None:
    """Background: AI review of a submitted task, then tell the hiring team it's ready for their decision."""
    async with AsyncSessionLocal() as db:
        try:
            task = await db.get(Assessment, assessment_id)
            app = await _application(db, organization_id, task.application_id)
            review = await screening_ai.review_assessment(app.job, task.title, task.instructions, task.submission)
            if review:
                task.ai_score, task.ai_recommendation, task.ai_feedback = (
                    review["score"], review["recommendation"], review["feedback"])
            _, hiring = _links()
            verdict = (f"The AI suggests {review['recommendation'].upper()} ({review['score']}/100): {review['feedback']}"
                       if review else "The AI couldn't review it, so it's all yours.")
            await email_hiring_team(
                db, organization_id, f"{app.candidate.full_name} submitted their task for {app.job.title}",
                f"{app.candidate.full_name} submitted \"{task.title}\".\n\n{verdict}\n\nRead it and decide: {hiring}",
                "assessment.submitted", {"assessment_id": task.id},
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Reviewing a task failed", extra={"assessment_id": assessment_id})


# ---------- video screens ----------

async def invite_video_screen(db: AsyncSession, organization_id: int, application_id: int, *,
                              questions: list[str] | None = None, due_days: int = 5) -> VideoScreen:
    app = await _application(db, organization_id, application_id)
    qs = [q.strip() for q in (questions or []) if q.strip()][:6] or default_questions(app.job.title)
    screen = VideoScreen(organization_id=organization_id, application_id=app.id, questions=qs, answers=[],
                         due_at=_due(due_days))
    db.add(screen)
    await db.flush()
    account, _ = _links()
    company = await company_name(db, organization_id)
    listed = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(qs))
    await email_applicant(
        db, organization_id, app.candidate.email, f"Short video questions for {app.job.title}",
        f"Hi {first_name(app.candidate.full_name)},\n\nWe'd like to hear from you. Please record a short video answer "
        f"(about a minute each) to these questions by {screen.due_at:%A %d %B}:\n\n{listed}\n\nYou can record right "
        f"in your browser, re-record as often as you like, and answer in English or Nepali: {account}\n\n{company}",
        "video_screen.invited", {"video_screen_id": screen.id},
    )
    return screen


async def _own_screen(db: AsyncSession, user: User, screen_id: int) -> VideoScreen:
    screen = (await db.execute(
        select(VideoScreen).join(Application, Application.id == VideoScreen.application_id)
        .where(VideoScreen.id == screen_id, Application.candidate_id == user.id)
    )).scalar_one_or_none()
    if not screen:
        raise hr_actions.NotFoundError("Video screen not found")
    if screen.status != "invited":
        raise ScreeningError("You've already sent your answers.")
    return screen


async def save_answer(db: AsyncSession, user: User, screen_id: int, index: int, data: bytes,
                      content_type: str, language: str | None = None) -> VideoScreen:
    screen = await _own_screen(db, user, screen_id)
    if not 0 <= index < len(screen.questions):
        raise ScreeningError("There's no such question.")
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in VIDEO_TYPES:
        raise ScreeningError("Please upload a video (WebM or MP4).")
    if not data:
        raise ScreeningError("The recording is empty.")
    key = f"org-{screen.organization_id}/screens/{screen.id}/{index}-{uuid.uuid4().hex}{VIDEO_TYPES[base_type]}"
    ref = await store_file(data, key, base_type)
    answers = [a for a in screen.answers if a["index"] != index]
    answers.append({"index": index, "file": ref, "content_type": base_type, "transcript": None,
                    "language": language if language in ("en", "ne") else None})
    screen.answers = sorted(answers, key=lambda a: a["index"])
    await db.flush()
    return screen


async def complete_screen(db: AsyncSession, user: User, screen_id: int) -> VideoScreen:
    screen = await _own_screen(db, user, screen_id)
    missing = set(range(len(screen.questions))) - {a["index"] for a in screen.answers}
    if missing:
        raise ScreeningError(f"Please answer question {min(missing) + 1} first.")
    screen.status, screen.completed_at = "completed", datetime.now(timezone.utc)
    await db.flush()
    return screen


async def review_screen_later(organization_id: int, screen_id: int) -> None:
    """Background: transcribe each answer, have the AI review them, then tell the hiring team."""
    async with AsyncSessionLocal() as db:
        try:
            screen = await db.get(VideoScreen, screen_id)
            app = (await db.execute(
                select(Application).where(Application.id == screen.application_id)
                .options(selectinload(Application.job), selectinload(Application.candidate))
            )).scalar_one()
            answers = []
            for a in screen.answers:
                if not a.get("transcript"):
                    data = await read_file(a["file"])
                    a = {**a, "transcript": await screening_ai.transcribe(
                        data, f"answer-{a['index']}{VIDEO_TYPES.get(a['content_type'], '.webm')}", a["content_type"],
                        a.get("language"))}
                if a.get("transcript") and "english" not in a:
                    a = {**a, "english": await screening_ai.english_version(a["transcript"])}
                answers.append(a)
            screen.answers = answers
            # The AI reviews the English version when the answer was spoken in Nepali.
            transcripts = [next((a.get("english") or a["transcript"] for a in answers if a["index"] == i), "") or ""
                           for i in range(len(screen.questions))]
            review = (await screening_ai.review_video_answers(app.job, screen.questions, transcripts)
                      if any(transcripts) else None)
            if review:
                screen.ai_score, screen.ai_recommendation, screen.ai_feedback = (
                    review["score"], review["recommendation"], review["feedback"])
            _, hiring = _links()
            verdict = (f"The AI suggests {review['recommendation'].upper()} ({review['score']}/100): {review['feedback']}"
                       if review else "The AI couldn't review the answers, so watch them yourself.")
            await email_hiring_team(
                db, organization_id, f"{app.candidate.full_name} recorded their video answers for {app.job.title}",
                f"{app.candidate.full_name} answered {len(screen.questions)} video questions.\n\n{verdict}\n\n"
                f"Watch and decide: {hiring}",
                "video_screen.completed", {"video_screen_id": screen.id},
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Reviewing a video screen failed", extra={"video_screen_id": screen_id})


# ---------- the human decision ----------

async def decide(db: AsyncSession, organization_id: int, kind: str, item_id: int, passed: bool,
                 reviewer_id: int) -> Assessment | VideoScreen:
    """A person passes or fails a submitted task or video screen. Failing rejects the application (the applicant
    is emailed); passing tells them they're moving on."""
    model = Assessment if kind == "assessment" else VideoScreen
    ready = "submitted" if kind == "assessment" else "completed"
    item = (await db.execute(
        select(model).where(model.id == item_id, model.organization_id == organization_id)
    )).scalar_one_or_none()
    if not item:
        raise hr_actions.NotFoundError("Not found")
    if item.status != ready:
        raise ScreeningError("This isn't waiting for a decision." if item.status in ("passed", "failed")
                             else "The applicant hasn't sent it yet.")
    item.status = "passed" if passed else "failed"
    item.reviewed_by_id, item.reviewed_at = reviewer_id, datetime.now(timezone.utc)
    await db.flush()
    app = (await db.execute(
        select(Application).where(Application.id == item.application_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )).scalar_one()
    if not passed:
        await hr_actions.set_application_status(db, organization_id, app.id, ApplicationStatus.REJECTED)
    else:
        what = "task" if kind == "assessment" else "video answers"
        await email_applicant(
            db, organization_id, app.candidate.email, f"Next step for {app.job.title}",
            f"Hi {first_name(app.candidate.full_name)},\n\nThanks for your {what}. We were impressed, and we'd like to "
            f"move you forward. We'll be in touch shortly about an interview.\n\n{await company_name(db, organization_id)}",
            f"{kind}.passed", {"id": item.id},
        )
    return item
