"""Reading uploaded documents (resumes, handbooks): size limits and text extraction."""

import asyncio
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from shared.services import vision
from shared.services.resume_parser import extract_text_from_file

DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    **vision.IMAGE_TYPES,
}


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    chunks, size = [], 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail=f"File exceeds {max_bytes // (1024 * 1024)} MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def extract_text(data: bytes, suffix: str) -> str:
    """Blocking; call it in a thread."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(data)
        return extract_text_from_file(path)


async def extract_document_text(data: bytes, suffix: str) -> tuple[str, bool]:
    """(text, read_from_scan). Photos and scanned PDFs (no text layer) are read by the vision model, which can
    misread names and numbers, especially in Devanagari; callers flag that."""
    if suffix in vision.IMAGE_TYPES:
        return await vision.read_image(data, vision.IMAGE_TYPES[suffix]), True
    text = await asyncio.to_thread(extract_text, data, suffix)
    if suffix == ".pdf" and len(text.strip()) < 80 and vision.configured():
        scanned = await vision.read_pdf_pages(data)
        if scanned:
            return scanned, True
    return text, False
