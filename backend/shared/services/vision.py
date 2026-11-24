"""Reading text from images of documents (scanned PDFs, photos) with a vision-language model.

Used only to turn pictures of documents into text. It never looks at people.
"""

import asyncio
import base64
import io
import logging

import httpx

from shared.core.config import get_settings

logger = logging.getLogger(__name__)

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

PROMPT = ("Transcribe all the text in this document image exactly as written, top to bottom. Keep headings, lists "
          "and line breaks. Keep Nepali in Devanagari script. Output only the text, with no commentary. If there is "
          "no readable text, output nothing.")


def _key() -> str | None:
    s = get_settings()
    return s.vision_llm_api_key or s.nvidia_api_key


def configured() -> bool:
    s = get_settings()
    # A local server (Ollama) needs no key.
    return bool(_key()) or "localhost" in s.vision_llm_base_url or "host.docker.internal" in s.vision_llm_base_url


async def read_image(data: bytes, mime: str) -> str:
    """Text in one image, or "" if the model isn't available."""
    s = get_settings()
    if not configured():
        return ""
    body = {
        "model": s.vision_llm_model, "temperature": 0, "max_tokens": 2000,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}},
        ]}],
    }
    headers = {"Authorization": f"Bearer {_key()}"} if _key() else {}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(f"{s.vision_llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=body)
        res.raise_for_status()
        return (res.json()["choices"][0]["message"]["content"] or "").strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        detail = exc.response.text[:200] if isinstance(exc, httpx.HTTPStatusError) else str(exc)
        logger.warning("Vision model failed: %s", detail)
        return ""


def pdf_pages_as_png(data: bytes, max_pages: int) -> list[bytes]:
    """Blocking: render the first pages of a PDF to PNG images (about 150 dpi)."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    try:
        images = []
        for i in range(min(len(pdf), max_pages)):
            bitmap = pdf[i].render(scale=150 / 72).to_pil()
            out = io.BytesIO()
            bitmap.convert("RGB").save(out, format="PNG", optimize=True)
            images.append(out.getvalue())
        return images
    finally:
        pdf.close()


async def read_pdf_pages(data: bytes) -> str:
    pages = await asyncio.to_thread(pdf_pages_as_png, data, get_settings().vision_max_pages)
    texts = [await read_image(page, "image/png") for page in pages]
    return "\n\n".join(t for t in texts if t)
