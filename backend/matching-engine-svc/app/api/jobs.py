import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.api.rbac import has_role, require_roles
from shared.db.session import get_db
from shared.models.entities import Job, Organization, User, UserRole
from shared.schemas.common import JDGenerateRequest, JDGenerateResponse, JobCreate, JobOut, JobUpdate
from shared.services.embeddings import COLLECTION_JOBS, upsert_vector
from shared.services.jd_generator import generate_job_description

router = APIRouter(prefix="/jobs", tags=["jobs"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


async def _index_job(job: Job) -> None:
    text = f"{job.title} {job.description} {' '.join(job.required_skills or [])}"
    await asyncio.to_thread(
        upsert_vector,
        COLLECTION_JOBS,
        f"job-{job.id}",
        text,
        {"job_id": job.id, "title": job.title, "organization_id": job.organization_id},
    )


@router.get("/public/{org_slug}", response_model=list[JobOut])
async def public_jobs(org_slug: str, db: AsyncSession = Depends(get_db, scope="function")):
    """Careers page: open roles for one organization, no login required."""
    result = await db.execute(
        select(Job)
        .join(Organization, Organization.id == Job.organization_id)
        .where(Organization.slug == org_slug, Organization.is_active, Job.status == "open")
        .order_by(Job.created_at.desc())
    )
    return result.scalars().all()


@router.get("", response_model=list[JobOut])
async def list_jobs(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)):
    query = select(Job).where(Job.organization_id == user.organization_id)
    if not has_role(user, (UserRole.ADMIN, UserRole.RECRUITER)):
        query = query.where(Job.status == "open")
    result = await db.execute(query.order_by(Job.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=JobOut, status_code=201)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    job = Job(**payload.model_dump(), organization_id=user.organization_id)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await _index_job(job)
    return job


@router.post("/generate", response_model=JDGenerateResponse)
async def generate_jd(payload: JDGenerateRequest, _: User = Depends(hr_staff)):
    return generate_job_description(payload)


async def _get_job(db: AsyncSession, job_id: int, organization_id: int) -> Job:
    job = (await db.execute(
        select(Job).where(Job.id == job_id, Job.organization_id == organization_id)
    )).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)):
    return await _get_job(db, job_id, user.organization_id)


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: int, payload: JobUpdate, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)
):
    job = await _get_job(db, job_id, user.organization_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    await db.flush()
    await db.refresh(job)
    await _index_job(job)
    return job
