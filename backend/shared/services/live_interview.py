"""The live interview: an in-app video call between the interviewer and the applicant, recorded only with the
applicant's consent, transcribed afterwards with AI notes, and a scorecard the interviewer fills in.

The call itself is peer-to-peer WebRTC between the two browsers. The server only passes the setup messages
(offer, answer, network candidates) between them, through the interview_signals table.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.config import get_settings
from shared.db.session import AsyncSessionLocal
from shared.models.entities import Application, CandidateProfile, Interview, InterviewSignal, User, UserRole
from shared.models.screening import Assessment, VideoScreen
from shared.services import interview_ai, screening_ai
from shared.services.events import publish_notification
from shared.services.hr_actions import NotFoundError
from shared.services.storage import read_file, store_file

logger = logging.getLogger(__name__)

AUDIO_TYPES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "video/webm": ".webm"}
CLIENT_SIGNALS = {"hello", "offer", "answer", "ice", "bye"}
MAX_SIGNAL_BYTES = 20_000


class InterviewError(ValueError):
    """Not allowed in the interview's current state (no consent, already ended …)."""


@dataclass
class Seat:
    interview: Interview
    application: Application
    role: str  # interviewer | candidate

    @property
    def other(self) -> str:
        return "candidate" if self.role == "interviewer" else "interviewer"


async def seat(db: AsyncSession, user: User, interview_id: int) -> Seat:
    """The interview and which side of the call this user is on. The hiring team of the company is the
    interviewer side; the applicant is the candidate side. Anyone else gets NotFound."""
    row = (await db.execute(
        select(Interview, Application).join(Application, Application.id == Interview.application_id)
        .where(Interview.id == interview_id, Interview.organization_id == user.organization_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )).one_or_none()
    if row:
        interview, application = row
        if user.role in (UserRole.ADMIN, UserRole.RECRUITER):
            return Seat(interview, application, "interviewer")
        if user.role == UserRole.CANDIDATE and application.candidate_id == user.id:
            return Seat(interview, application, "candidate")
    raise NotFoundError("Interview not found")


def ice_servers() -> list[dict]:
    try:
        servers = json.loads(get_settings().webrtc_ice_servers)
        return servers if isinstance(servers, list) else []
    except ValueError:
        logger.warning("WEBRTC_ICE_SERVERS isn't valid JSON")
        return []


async def _signal(db: AsyncSession, interview_id: int, to_role: str, kind: str, data: dict | None = None) -> None:
    db.add(InterviewSignal(interview_id=interview_id, to_role=to_role, kind=kind, data=data or {}))
    await db.flush()


async def join(db: AsyncSession, user: User, interview_id: int) -> tuple[Seat, int]:
    """Enter the call room. Returns the seat and the signal cursor to wait from; tells the other side we're here."""
    s = await seat(db, user, interview_id)
    if s.interview.status == "cancelled":
        raise InterviewError("This interview was cancelled.")
    cursor = (await db.execute(select(func.coalesce(func.max(InterviewSignal.id), 0))
                               .where(InterviewSignal.interview_id == interview_id))).scalar_one()
    if s.role == "interviewer" and not s.interview.started_at:
        s.interview.started_at = datetime.now(timezone.utc)
    await _signal(db, interview_id, s.other, "hello")
    return s, cursor


async def send_signal(db: AsyncSession, user: User, interview_id: int, kind: str, data: dict) -> None:
    if kind not in CLIENT_SIGNALS:
        raise InterviewError("Unknown signal.")
    if len(json.dumps(data)) > MAX_SIGNAL_BYTES:
        raise InterviewError("Signal too large.")
    s = await seat(db, user, interview_id)
    await _signal(db, interview_id, s.other, kind, data)


async def wait_signals(user: User, interview_id: int, after: int, timeout: float = 20.0) -> tuple[list[dict], int]:
    """Long poll: messages for this user's side newer than `after`, waiting up to `timeout` seconds for some.
    Uses a short session per check so a waiting browser doesn't hold a database connection."""
    async with AsyncSessionLocal() as db:
        role = (await seat(db, user, interview_id)).role
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(InterviewSignal).where(InterviewSignal.interview_id == interview_id,
                                              InterviewSignal.to_role == role, InterviewSignal.id > after)
                .order_by(InterviewSignal.id).limit(100)
            )).scalars().all()
        if rows or asyncio.get_running_loop().time() >= deadline:
            messages = [{"id": r.id, "kind": r.kind, "data": r.data} for r in rows]
            return messages, rows[-1].id if rows else after
        await asyncio.sleep(0.4)


async def set_consent(db: AsyncSession, user: User, interview_id: int, allowed: bool) -> Interview:
    """The applicant allows or refuses recording, at any time. Refusing stops a recording in progress."""
    s = await seat(db, user, interview_id)
    if s.role != "candidate":
        raise InterviewError("Only the applicant can give or withdraw consent to recording.")
    s.interview.recording_consent = allowed
    s.interview.recording_consent_at = datetime.now(timezone.utc)
    if not allowed:
        s.interview.recording_on = False
    await _signal(db, interview_id, "interviewer", "consent", {"allowed": allowed})
    return s.interview


async def set_recording(db: AsyncSession, user: User, interview_id: int, on: bool) -> Interview:
    s = await seat(db, user, interview_id)
    if s.role != "interviewer":
        raise InterviewError("Only the interviewer controls recording.")
    if on and not s.interview.recording_consent:
        raise InterviewError("The applicant hasn't agreed to recording.")
    if s.interview.status != "scheduled":
        raise InterviewError("This interview has ended.")
    s.interview.recording_on = on
    await _signal(db, interview_id, "candidate", "recording", {"on": on})
    return s.interview


async def save_part(db: AsyncSession, user: User, interview_id: int, *, part: int, track: str, offset: float,
                    language: str | None, data: bytes, content_type: str) -> None:
    """One piece of the recording: a few minutes of one speaker's audio, starting `offset` seconds into the call."""
    s = await seat(db, user, interview_id)
    if s.role != "interviewer":
        raise InterviewError("Only the interviewer's browser uploads the recording.")
    if not s.interview.recording_consent:
        raise InterviewError("The applicant hasn't agreed to recording.")
    if track not in ("interviewer", "candidate"):
        raise InterviewError("Unknown track.")
    base = content_type.split(";")[0].strip().lower()
    if base not in AUDIO_TYPES:
        raise InterviewError("Please upload audio (WebM, Ogg or MP4).")
    if not data:
        return
    key = f"org-{s.interview.organization_id}/interviews/{interview_id}/{part}-{track}-{uuid.uuid4().hex}{AUDIO_TYPES[base]}"
    ref = await store_file(data, key, base)
    parts = [p for p in s.interview.recording if not (p["part"] == part and p["track"] == track)]
    parts.append({"part": part, "track": track, "offset": max(0.0, offset), "file": ref, "content_type": base,
                  "language": language if language in ("en", "ne") else None})
    s.interview.recording = sorted(parts, key=lambda p: (p["part"], p["track"]))
    await db.flush()


async def finish(db: AsyncSession, user: User, interview_id: int) -> Interview:
    """The interviewer ends the call. If anything was recorded, notes are prepared in the background."""
    s = await seat(db, user, interview_id)
    if s.role != "interviewer":
        raise InterviewError("Only the interviewer can end the interview.")
    iv = s.interview
    if iv.status == "scheduled":
        iv.status, iv.ended_at, iv.recording_on = "completed", datetime.now(timezone.utc), False
        iv.summary_status = "processing" if iv.recording else ""
        await _signal(db, interview_id, "candidate", "bye")
    return iv


def merge_turns(lines: list[dict]) -> list[dict]:
    """Joins back-to-back pieces from the same speaker (Whisper splits mid-sentence) into one turn."""
    merged: list[dict] = []
    for line in lines:
        if merged and merged[-1]["speaker"] == line["speaker"]:
            merged[-1] = {**merged[-1], "text": f"{merged[-1]['text']} {line['text']}"}
        else:
            merged.append(dict(line))
    return merged


async def process_later(organization_id: int, interview_id: int) -> None:
    """Background: transcribe both speakers, put the lines in order, translate Nepali, write the AI notes, and
    email the interviewer that they're ready."""
    async with AsyncSessionLocal() as db:
        try:
            iv = (await db.execute(select(Interview).where(
                Interview.id == interview_id, Interview.organization_id == organization_id))).scalar_one()
            app = (await db.execute(select(Application).where(Application.id == iv.application_id)
                                    .options(selectinload(Application.job), selectinload(Application.candidate))
                                    )).scalar_one()
            lines = []
            for p in iv.recording:
                audio = await read_file(p["file"])
                for start, text in await screening_ai.transcribe_timed(
                        audio, f"part-{p['part']}-{p['track']}{AUDIO_TYPES[p['content_type']]}", p["content_type"],
                        p.get("language")):
                    lines.append({"at": round(p["offset"] + start, 1), "speaker": p["track"], "text": text})
            lines = merge_turns(sorted(lines, key=lambda line: line["at"]))
            iv.transcript = lines
            text = interview_ai.format_transcript(lines)
            iv.transcript_english = await interview_ai.english_transcript(text)
            iv.summary = await interview_ai.summarize(app.job, iv.transcript_english or text) if lines else None
            iv.summary_status = "ready" if iv.summary else "failed"
            base = get_settings().frontend_url.rstrip("/")
            name = app.candidate.full_name if app.candidate else "the applicant"
            await publish_notification(
                db, organization_id=organization_id, recipient=iv.interviewer_email, channel="email",
                subject=f"Interview notes ready: {name}",
                body=(f"The transcript{' and AI notes' if iv.summary else ''} from your interview with {name} for "
                      f"{app.job.title} are ready. Fill in your scorecard while it's fresh: {base}/interview/{iv.id}"
                      "\n\nThe AI notes only cover what was said. The decision is yours."),
                event_type="interview.notes_ready", payload={"interview_id": iv.id}, send_now=True,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Processing an interview recording failed", extra={"interview_id": interview_id})
            async with AsyncSessionLocal() as db:
                iv = await db.get(Interview, interview_id)
                if iv:
                    iv.summary_status = "failed"
                    await db.commit()


async def prepare_questions(db: AsyncSession, user: User, interview_id: int) -> Interview:
    s = await seat(db, user, interview_id)
    if s.role != "interviewer":
        raise NotFoundError("Interview not found")
    app = s.application
    profile = (await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == app.candidate_id))
               ).scalar_one_or_none()
    resume = ""
    if profile:
        resume = (f"Skills: {', '.join(profile.skills or [])}\nExperience: {profile.experience_years} years\n"
                  f"Education: {profile.education or '-'}\n\n{(profile.resume_text or '')[:4000]}")
    notes = []
    for t in (await db.execute(select(Assessment).where(Assessment.application_id == app.id))).scalars():
        if t.ai_feedback:
            notes.append(f"Task '{t.title}' ({t.status}): {t.ai_feedback}")
    for v in (await db.execute(select(VideoScreen).where(VideoScreen.application_id == app.id))).scalars():
        if v.ai_feedback:
            notes.append(f"Recorded answers ({v.status}): {v.ai_feedback}")
    if app.match_explanation:
        missing = app.match_explanation.get("missing_skills") or []
        if missing:
            notes.append(f"Skills not found in the resume: {', '.join(missing)}")
    questions = await interview_ai.prep_questions(app.job, resume, "\n".join(notes))
    if not questions:
        raise InterviewError("The AI couldn't prepare questions right now. Try again in a minute.")
    s.interview.prep_questions = questions
    return s.interview


async def save_scorecard(db: AsyncSession, user: User, interview_id: int, *, rating: int, recommendation: str,
                         notes: str) -> Interview:
    s = await seat(db, user, interview_id)
    if s.role != "interviewer":
        raise NotFoundError("Interview not found")
    s.interview.scorecard = {"rating": rating, "recommendation": recommendation, "notes": notes,
                             "by": user.full_name, "at": datetime.now(timezone.utc).isoformat()}
    return s.interview
