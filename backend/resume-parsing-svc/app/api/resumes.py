import asyncio
import tempfile
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
from shared.services.resume_parser import extract_text_from_file, parse_resume_text
from shared.services.storage import store_file

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_SUFFIXES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


@router.post("/parse-text", response_model=ParsedResume)
async def parse_text(body: ResumeText, _: User = Depends(require_user)):
    return parse_resume_text(body.text)


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    chunks, size = [], 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail=f"File exceeds {max_bytes // (1024 * 1024)} MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _extract(data: bytes, suffix: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"resume{suffix}"
        path.write_bytes(data)
        return extract_text_from_file(path)


@router.post("/upload", response_model=ParsedResume)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT, MD")

    data = await _read_limited(file, settings.max_upload_mb * 1024 * 1024)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    try:
        text = await asyncio.to_thread(_extract, data, suffix)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read this file. Is it a valid document?") from None
    parsed = parse_resume_text(text)

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
