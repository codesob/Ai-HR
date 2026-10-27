import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Application, ApplicationStatus, CandidateProfile, Job, User, UserRole
from shared.schemas.common import ApplicationOut, ApplicationStatusUpdate, ParsedResume
from shared.services.events import publish_notification
from shared.services.matching import compute_match, rank_applications, rerank_candidates_with_nvidia

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


@router.post("/apply/{job_id}", response_model=ApplicationOut, status_code=201)
async def apply_to_job(
    job_id: int,
    source: str = Query(default="careers_page", max_length=64),
    user: User = Depends(candidate_only),
    db: AsyncSession = Depends(get_db),
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
    parsed = ParsedResume(**(profile.parsed_data or {})) if profile and profile.parsed_data else ParsedResume()
    if profile and profile.skills:
        parsed.skills = profile.skills
        parsed.experience_years = profile.experience_years

    # Embedding is CPU-bound; keep the event loop free for other requests.
    match = await asyncio.to_thread(
        compute_match,
        parsed,
        job.description,
        job.required_skills or [],
        job.min_experience_years,
        profile.resume_text if profile else None,
    )

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

    recruiters = (await db.execute(
        select(User.email).where(
            User.organization_id == user.organization_id,
            User.role.in_([UserRole.RECRUITER, UserRole.ADMIN]),
            User.is_active,
        )
    )).scalars().all()
    for email in recruiters:
        await publish_notification(
            db,
            organization_id=user.organization_id,
            recipient=email,
            subject="New application received",
            body=f"{user.full_name} applied to {job.title}",
            event_type="application.created",
            payload={"application_id": app.id, "job_id": job.id, "candidate_id": user.id},
        )
    app.job, app.candidate = job, user
    await db.refresh(app, attribute_names=["created_at"])
    return _to_out(app)


@router.get("/mine", response_model=list[ApplicationOut])
async def my_applications(user: User = Depends(candidate_only), db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(hr_staff),
):
    app = (await db.execute(
        select(Application)
        .where(Application.id == application_id, Application.organization_id == user.organization_id)
        .options(selectinload(Application.job), selectinload(Application.candidate))
    )).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    new_status = ApplicationStatus(payload.status)
    app.status = new_status
    app.hired_at = datetime.now(timezone.utc) if new_status == ApplicationStatus.HIRED else None
    await db.flush()
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
async def ranked_candidates(job_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(hr_staff)):
    _, apps = await _job_applications(db, job_id, user.organization_id)
    profiles = await _profiles_by_user(db, [a.candidate_id for a in apps])
    items = [
        {
            "application_id": a.id,
            "candidate_id": a.candidate_id,
            "candidate_name": a.candidate.full_name if a.candidate else None,
            "status": a.status.value,
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
    db: AsyncSession = Depends(get_db),
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
