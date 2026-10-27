import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.rbac import require_roles
from shared.db.session import AsyncSessionLocal, get_db
from shared.models.entities import Application, ApplicationStatus, CandidateProfile, Job, User, UserRole
from shared.schemas.common import ApplicationOut, ApplicationStatusUpdate, MatchExplanation, ParsedResume
from shared.services.candidate_emails import company_name, email_applicant, email_hiring_team, stage_message
from shared.services.agent.triggers import screen_new_application
from shared.services.hr_actions import NotFoundError, set_application_status
from shared.services.matching import compute_match, rank_applications, rerank_candidates_with_nvidia

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)
candidate_only = require_roles(UserRole.CANDIDATE)


def _to_out(a: Application) -> ApplicationOut:
    return ApplicationOut(
        id=a.id,
        job_id=a.job_id,
        candidate_id=a.candidate_id,
        status=a.status.value,
        match_score=a.match_score,
        rank_score=a.rank_score,
        match_explanation=a.match_explanation,
        source=a.source,
        created_at=a.created_at,
        candidate_name=a.candidate.full_name if a.candidate else None,
        job_title=a.job.title if a.job else None,
    )


async def _profiles_by_user(db: AsyncSession, user_ids: list[int]) -> dict[int, CandidateProfile]:
    if not user_ids:
        return {}
    rows = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id.in_(user_ids)))
    return {p.user_id: p for p in rows.scalars()}


async def _score(job: Job, profile: CandidateProfile | None) -> MatchExplanation:
    parsed = ParsedResume(**(profile.parsed_data or {})) if profile and profile.parsed_data else ParsedResume()
    if profile and profile.skills:
        parsed.skills = profile.skills
        parsed.experience_years = profile.experience_years

    # Embedding is CPU-bound; keep the event loop free for other requests.
    return await asyncio.to_thread(
        compute_match,
        parsed,
        job.description,
        job.required_skills or [],
        job.min_experience_years,
        profile.resume_text if profile else None,
    )


async def score_unscored_applications() -> None:
    """Score applications created outside the apply flow (imports, demo data) with the real matching model."""
    async with AsyncSessionLocal() as db:
        apps = (await db.execute(
            select(Application).where(Application.match_score.is_(None)).options(selectinload(Application.job))
        )).scalars().all()
        if not apps:
            return
        profiles = await _profiles_by_user(db, list({a.candidate_id for a in apps}))
        for app in apps:
            match = await _score(app.job, profiles.get(app.candidate_id))
            app.match_score = app.rank_score = match.match_score
            app.match_explanation = match.model_dump()
        await db.commit()
        logger.info("Scored unscored applications", extra={"count": len(apps)})


@router.post("/apply/{job_id}", response_model=ApplicationOut, status_code=201)
async def apply_to_job(
    job_id: int,
    background: BackgroundTasks,
    source: str = Query(default="careers_page", max_length=64),
    user: User = Depends(candidate_only),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    job = (await db.execute(
        select(Job).where(Job.id == job_id, Job.organization_id == user.organization_id, Job.status == "open")
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await db.execute(
        select(Application.id).where(Application.job_id == job_id, Application.candidate_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already applied") from None

    profile = (await _profiles_by_user(db, [user.id])).get(user.id)
    match = await _score(job, profile)

    app = Application(
        organization_id=user.organization_id,
        job_id=job_id,
        candidate_id=user.id,
        status=ApplicationStatus.APPLIED,
        source=source,
        match_score=match.match_score,
        rank_score=match.match_score,
        match_explanation=match.model_dump(),
    )
    db.add(app)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Already applied") from None

    company = await company_name(db, user.organization_id)
    subject, body = stage_message("applied", user.full_name, job.title, company)
    await email_applicant(db, user.organization_id, user.email, subject, body, "application.received",
                          {"application_id": app.id})
    via = " via LinkedIn" if source == "linkedin" else ""
    await email_hiring_team(
        db, user.organization_id, f"New application{via}: {user.full_name} for {job.title}",
        f"{user.full_name} applied for {job.title}{via}. Match with the job: {round((match.match_score or 0) * 100)}/100."
        "\n\nThe HR agent reads the resume next and will tell you if anything needs your OK.",
        "application.created", {"application_id": app.id, "job_id": job.id, "candidate_id": user.id},
    )
    app.job, app.candidate = job, user
    await db.refresh(app, attribute_names=["created_at"])
    # Runs after the response, once this request's transaction has committed.
    background.add_task(screen_new_application, user.organization_id, app.id)
    return _to_out(app)


@router.get("/mine", response_model=list[ApplicationOut])
async def my_applications(user: User = Depends(candidate_only), db: AsyncSession = Depends(get_db, scope="function")):
    result = await db.execute(
        select(Application)
        .where(Application.candidate_id == user.id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
        .order_by(Application.created_at.desc())
    )
    return [_to_out(a) for a in result.scalars()]


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    job_id: int | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    q = (
        select(Application)
        .where(Application.organization_id == user.organization_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )
    if job_id:
        q = q.where(Application.job_id == job_id)
    result = await db.execute(q.order_by(Application.rank_score.desc().nullslast()))
    return [_to_out(a) for a in result.scalars()]


@router.patch("/{application_id}/status", response_model=ApplicationOut)
async def update_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    try:
        app = await set_application_status(db, user.organization_id, application_id, ApplicationStatus(payload.status))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    return _to_out(app)


async def _job_applications(db: AsyncSession, job_id: int, organization_id: int) -> tuple[Job, list[Application]]:
    job = (await db.execute(
        select(Job).where(Job.id == job_id, Job.organization_id == organization_id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    apps = (await db.execute(
        select(Application).where(Application.job_id == job_id).options(selectinload(Application.candidate))
    )).scalars().all()
    return job, list(apps)


@router.get("/ranked/{job_id}")
async def ranked_candidates(job_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    _, apps = await _job_applications(db, job_id, user.organization_id)
    profiles = await _profiles_by_user(db, [a.candidate_id for a in apps])
    items = [
        {
            "application_id": a.id,
            "candidate_id": a.candidate_id,
            "candidate_name": a.candidate.full_name if a.candidate else None,
            "status": a.status.value,
            "source": a.source,
            "match_score": a.match_score,
            "match_explanation": a.match_explanation,
            "parsed_data": (profiles[a.candidate_id].parsed_data if a.candidate_id in profiles else None) or {},
        }
        for a in apps
    ]
    ranked = rank_applications(items)
    by_id = {a.id: a for a in apps}
    for item in ranked:
        by_id[item["application_id"]].rank_score = item["rank_score"]
    return ranked


@router.get("/reranked/{job_id}")
async def reranked_candidates_nvidia(
    job_id: int,
    top_k: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(hr_staff),
):
    """Semantic reranking with NVIDIA Nemotron; falls back to stored order if the API is unavailable."""
    job, apps = await _job_applications(db, job_id, user.organization_id)
    if not apps:
        return []
    profiles = await _profiles_by_user(db, [a.candidate_id for a in apps])
    candidates = []
    for a in apps:
        profile = profiles.get(a.candidate_id)
        candidates.append({
            "id": a.candidate_id,
            "name": a.candidate.full_name if a.candidate else None,
            "application_id": a.id,
            "resume_text": (profile.resume_text if profile else "") or "",
            "match_score": a.match_score,
            "rank_score": a.rank_score,
            "parsed_data": (profile.parsed_data if profile else None) or {},
        })

    reranked = await rerank_candidates_with_nvidia(job_description=job.description, candidates=candidates, top_k=top_k)
    return [
        {
            **c,
            "rank_position": idx + 1,
            "rerank_score": c.get("rerank_score"),
            "improvement": (
                round(c["rerank_score"] - (c.get("original_score") or 0.0), 3)
                if c.get("rerank_score") is not None else None
            ),
        }
        for idx, c in enumerate(reranked)
    ]
