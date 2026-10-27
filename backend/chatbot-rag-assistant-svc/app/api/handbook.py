import asyncio
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.core.config import get_settings
from shared.db.session import get_db
from shared.models.entities import User, UserRole
from shared.models.handbook import PolicyDocument
from shared.services import handbook
from shared.services.uploads import DOCUMENT_TYPES, extract_document_text, read_limited

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/handbook", tags=["handbook"])

admin_only = require_roles(UserRole.ADMIN)


class PolicyDocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    chunks: int
    characters: int
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[PolicyDocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(admin_only)):
    rows = await db.execute(
        select(PolicyDocument).where(PolicyDocument.organization_id == user.organization_id)
        .order_by(PolicyDocument.created_at.desc())
    )
    return rows.scalars().all()


@router.post("", response_model=PolicyDocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(admin_only),
):
    name = Path(file.filename or "").name
    suffix = Path(name).suffix.lower()
    if suffix not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT, MD, or a photo (PNG, JPG)")
    data = await read_limited(file, get_settings().max_upload_mb * 1024 * 1024)
    try:
        text, _ = await extract_document_text(data, suffix)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read this file. Is it a valid document?") from None
    chunks = handbook.chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="We couldn't find any readable text in this file.")

    doc = PolicyDocument(
        organization_id=user.organization_id, title=Path(name).stem.replace("_", " ").replace("-", " ")[:255],
        filename=name[:255], chunks=len(chunks), characters=len(text), uploaded_by_id=user.id,
    )
    db.add(doc)
    await db.flush()
    try:
        await asyncio.to_thread(handbook.index_document, doc, chunks)
    except Exception:
        logger.exception("Handbook indexing failed")
        raise HTTPException(status_code=503, detail="The policy library is unavailable. Try again shortly.") from None
    await db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(admin_only)
):
    doc = (await db.execute(
        select(PolicyDocument).where(PolicyDocument.id == document_id, PolicyDocument.organization_id == user.organization_id)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        await asyncio.to_thread(handbook.remove_document, doc)
    except Exception:
        logger.exception("Handbook removal failed")
        raise HTTPException(status_code=503, detail="The policy library is unavailable. Try again shortly.") from None
    await db.delete(doc)
