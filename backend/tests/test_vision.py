"""Scanned PDFs and photos of documents are read by the vision model; normal documents never touch it."""

import io

import httpx
import pytest
from pypdf import PdfWriter

from shared.services import uploads, vision


def _blank_pdf(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def seen(monkeypatch):
    calls: list[str] = []

    async def read_image(data: bytes, mime: str) -> str:
        calls.append(mime)
        return f"Text read from a {mime} image"

    monkeypatch.setattr(vision, "read_image", read_image)
    monkeypatch.setattr(vision, "configured", lambda: True)
    return calls


async def test_photos_are_read_by_the_vision_model(seen):
    assert await uploads.extract_document_text(b"\x89PNG...", ".png") == ("Text read from a image/png image", True)
    assert ".jpg" in uploads.DOCUMENT_TYPES


async def test_scanned_pdf_pages_are_rendered_and_read(seen):
    text, from_scan = await uploads.extract_document_text(_blank_pdf(2), ".pdf")
    assert from_scan
    assert seen == ["image/png", "image/png"]
    assert text.count("Text read from") == 2


async def test_documents_with_text_skip_the_vision_model(seen):
    text, from_scan = await uploads.extract_document_text(b"Senior engineer with Python and FastAPI. " * 5, ".txt")
    assert not from_scan
    assert "Python" in text and seen == []


def test_pdf_pages_render_to_png_and_respect_the_page_cap():
    pages = vision.pdf_pages_as_png(_blank_pdf(5), max_pages=3)
    assert len(pages) == 3 and all(p.startswith(b"\x89PNG") for p in pages)


async def test_vision_call_sends_the_image_and_survives_errors(monkeypatch):
    from shared.core.config import get_settings

    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["url"] = str(request.url)
        sent["body"] = request.read()
        return httpx.Response(200, json={"choices": [{"message": {"content": " Sita Sharma\nसीप "}}]})

    monkeypatch.setattr(get_settings(), "vision_llm_api_key", "k")
    real = httpx.AsyncClient
    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    assert await vision.read_image(b"img", "image/jpeg") == "Sita Sharma\nसीप"
    assert sent["url"].endswith("/chat/completions") and b"data:image/jpeg;base64,aW1n" in sent["body"]

    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: real(
        transport=httpx.MockTransport(lambda r: httpx.Response(402, text="no credits")), **kw))
    assert await vision.read_image(b"img", "image/jpeg") == ""


async def test_resume_skills_come_from_the_model_for_any_field(monkeypatch):
    from shared.services import resume_parser
    from shared.services.agent import llm

    async def complete(messages, tools):
        return llm.LLMReply(content='{"name": "Sita Sharma", "skills": ["Figma", "User Research", "Prototyping"], '
                                    '"experience_years": 6, "education": "BFA, Tribhuvan University", '
                                    '"summary": "Product designer."}')

    monkeypatch.setattr(llm, "configured", lambda: True)
    monkeypatch.setattr(llm, "complete", complete)
    text = "Sita Sharma\nsita@example.com +977 9800000000\nFigma, प्रोटोटाइपिङ, प्रयोगकर्ता अनुसन्धान\nLeapfrog 2019 - 2025"
    assert resume_parser.parse_resume_text(text).skills == []  # the old keyword list knows only programming terms
    parsed = await resume_parser.parse_resume_smart(text)
    assert parsed.skills == ["Figma", "User Research", "Prototyping"]
    assert parsed.education == "BFA, Tribhuvan University" and parsed.experience_years == 6
    assert parsed.email == "sita@example.com"  # contact details from the patterns, not the model

    async def broken(messages, tools):
        raise llm.AgentLLMError("down")

    monkeypatch.setattr(llm, "complete", broken)
    assert (await resume_parser.parse_resume_smart(text)).email == "sita@example.com"
