from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.api.deps import require_user
from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Application, ApplicationStatus, CandidateProfile, Job, User, UserRole
from shared.schemas.common import ApplicationOut, ParsedResume
from shared.services.events import publish_notification
from shared.services.matching import compute_match, rank_applications

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/apply/{job_id}", response_model=ApplicationOut)
async def apply_to_job(
    job_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await db.execute(
        select(Application).where(
            Application.job_id == job_id, Application.candidate_id == user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already applied")

    prof_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = prof_result.scalar_one_or_none()
    parsed = ParsedResume(**(profile.parsed_data or {})) if profile and profile.parsed_data else ParsedResume()
    if profile and profile.skills:
        parsed.skills = profile.skills
        parsed.experience_years = profile.experience_years

    match = compute_match(
        parsed,
        job.description,
        job.required_skills or [],
        job.min_experience_years,
        profile.resume_text if profile else None,
    )

    app = Application(
        job_id=job_id,
        candidate_id=user.id,
        status=ApplicationStatus.APPLIED,
        match_score=match.match_score,
        rank_score=match.match_score,
        match_explanation=match.model_dump(),
    )
    db.add(app)
    await db.flush()
    await publish_notification(
        db,
        recipient="recruiter@aihr.demo",
        subject="New application received",
        body=f"{user.full_name} applied to {job.title}",
        event_type="application.created",
        payload={"application_id": app.id, "job_id": job.id, "candidate_id": user.id},
    )
    await db.refresh(app)
    return ApplicationOut(
        id=app.id,
        job_id=app.job_id,
        candidate_id=app.candidate_id,
        status=app.status.value,
        match_score=app.match_score,
        rank_score=app.rank_score,
        match_explanation=app.match_explanation,
        created_at=app.created_at,
        candidate_name=user.full_name,
        job_title=job.title,
    )


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    job_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    q = select(Application).options(
        selectinload(Application.job), selectinload(Application.candidate)
    )
    if job_id:
        q = q.where(Application.job_id == job_id)
    result = await db.execute(q.order_by(Application.rank_score.desc().nullslast()))
    apps = result.scalars().all()
    return [
        ApplicationOut(
            id=a.id,
            job_id=a.job_id,
            candidate_id=a.candidate_id,
            status=a.status.value,
            match_score=a.match_score,
            rank_score=a.rank_score,
            match_explanation=a.match_explanation,
            created_at=a.created_at,
            candidate_name=a.candidate.full_name if a.candidate else None,
            job_title=a.job.title if a.job else None,
        )
        for a in apps
    ]


@router.get("/ranked/{job_id}")
async def ranked_candidates(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    result = await db.execute(
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.candidate))
    )
    apps = result.scalars().all()
    items = []
    for a in apps:
        prof = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == a.candidate_id)
        )
        profile = prof.scalar_one_or_none()
        items.append({
            "application_id": a.id,
            "candidate_id": a.candidate_id,
            "candidate_name": a.candidate.full_name if a.candidate else None,
            "status": a.status.value,
            "match_score": a.match_score,
            "match_explanation": a.match_explanation,
            "parsed_data": profile.parsed_data if profile else {},
        })
    ranked = rank_applications(items)
    for i, item in enumerate(ranked):
        app = next(a for a in apps if a.id == item["application_id"])
        app.rank_score = item["rank_score"]
    return ranked
