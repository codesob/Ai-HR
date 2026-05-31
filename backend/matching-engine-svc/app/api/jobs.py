from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import Job, User, UserRole
from shared.schemas.common import JDGenerateRequest, JDGenerateResponse, JobCreate, JobOut
from shared.services.embeddings import COLLECTION_JOBS, upsert_vector
from shared.services.jd_generator import generate_job_description

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=JobOut)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    job = Job(**payload.model_dump())
    db.add(job)
    await db.flush()
    await db.refresh(job)
    text = f"{job.title} {job.description} {' '.join(job.required_skills)}"
    upsert_vector(COLLECTION_JOBS, str(job.id), text, {"job_id": job.id, "title": job.title})
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/generate", response_model=JDGenerateResponse)
async def generate_jd(
    payload: JDGenerateRequest,
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    return generate_job_description(payload)
