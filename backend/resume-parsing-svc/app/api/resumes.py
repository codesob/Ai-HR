import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.core.config import get_settings
from shared.db.session import get_db
from shared.models.entities import CandidateProfile, User
from shared.schemas.common import ParsedResume
from shared.services.embeddings import COLLECTION_RESUMES, upsert_vector
from shared.services.resume_parser import parse_resume_file, parse_resume_text
from shared.services.storage import save_upload

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/parse-text", response_model=ParsedResume)
async def parse_text(body: dict):
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return parse_resume_text(text)


@router.post("/upload", response_model=ParsedResume)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc", ".txt", ".md"):
        raise HTTPException(status_code=400, detail="Supported: PDF, DOCX, TXT")

    file_id = f"{user.id}_{uuid.uuid4().hex}{suffix}"
    dest = await save_upload(file, file_id)

    parsed = await parse_resume_file(dest)

    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)

    profile.resume_text = dest.read_text(encoding="utf-8", errors="ignore") if suffix == ".txt" else None
    if not profile.resume_text:
        from shared.services.resume_parser import extract_text_from_file
        profile.resume_text = extract_text_from_file(dest)
    profile.parsed_data = parsed.model_dump()
    profile.skills = parsed.skills
    profile.experience_years = parsed.experience_years
    profile.education = parsed.education
    profile.resume_file_path = str(dest)

    text_for_vector = f"{parsed.name} {' '.join(parsed.skills)} {profile.resume_text or ''}"
    upsert_vector(
        COLLECTION_RESUMES,
        str(user.id),
        text_for_vector[:8000],
        {"user_id": user.id, "skills": parsed.skills},
    )
    await db.flush()
    return parsed
