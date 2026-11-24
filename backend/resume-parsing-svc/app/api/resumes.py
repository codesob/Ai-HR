import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.core.config import get_settings
from shared.db.session import get_db
from shared.models.entities import CandidateProfile, User
from shared.schemas.common import ParsedResume, ResumeText
from shared.services.embeddings import COLLECTION_RESUMES, upsert_vector
from shared.services.resume_parser import parse_resume_smart
from shared.services.storage import store_file
from shared.services.uploads import DOCUMENT_TYPES, extract_document_text, read_limited

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_SUFFIXES = DOCUMENT_TYPES


@router.post("/parse-text", response_model=ParsedResume)
async def parse_text(body: ResumeText, _: User = Depends(require_user)):
    return await parse_resume_smart(body.text)




@router.post("/upload", response_model=ParsedResume)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT, MD, or a photo (PNG, JPG)")

    data = await read_limited(file, settings.max_upload_mb * 1024 * 1024)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    try:
        text, from_scan = await extract_document_text(data, suffix)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read this file. Is it a valid document?") from None
    parsed = (await parse_resume_smart(text)).model_copy(update={"read_from_scan": from_scan})

    key = f"org-{user.organization_id}/resumes/{user.id}_{uuid.uuid4().hex}{suffix}"
    stored_at = await store_file(data, key, ALLOWED_SUFFIXES[suffix])

    profile = (await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )).scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(user_id=user.id, organization_id=user.organization_id)
        db.add(profile)

    profile.resume_text = text
    profile.parsed_data = parsed.model_dump()
    profile.skills = parsed.skills
    profile.experience_years = parsed.experience_years
    profile.education = parsed.education
    profile.resume_file_path = stored_at
    await db.flush()

    await asyncio.to_thread(
        upsert_vector,
        COLLECTION_RESUMES,
        f"user-{user.id}",
        f"{parsed.name or ''} {' '.join(parsed.skills)} {text}"[:8000],
        {"user_id": user.id, "skills": parsed.skills, "organization_id": user.organization_id},
    )
    return parsed
