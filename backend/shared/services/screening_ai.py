"""AI side of screening: transcribing video answers and reviewing tasks and answers against the job.

The AI only recommends. A person always makes the pass/fail decision.
"""

import json
import logging
import re

import httpx

from shared.core.config import get_settings
from shared.models.entities import Job
from shared.services.agent import llm

logger = logging.getLogger(__name__)

REVIEW_RULES = """You review job applicants' work for a hiring team. Judge only what was asked and the job's stated
requirements. Never consider or guess age, gender, ethnicity, accent, appearance, disability, religion or family
status. Answers may be in English, Nepali or a mix: judge what is said, never the language, accent or fluency.
If an answer is empty or off-topic, say so. Write the feedback in English. Reply with JSON only:
{"score": <0-100>, "recommendation": "pass" or "fail", "feedback": "<3-5 short sentences a hiring manager can check>"}"""


class Review(dict):
    """{"score": int, "recommendation": "pass"|"fail", "feedback": str}"""


def _parse(content: str) -> Review | None:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        score = max(0, min(100, int(data["score"])))
        rec = "pass" if str(data.get("recommendation", "")).lower().startswith("pass") else "fail"
        return Review(score=score, recommendation=rec, feedback=str(data.get("feedback", ""))[:2000])
    except (ValueError, KeyError, TypeError):
        return None


async def _review(prompt: str) -> Review | None:
    if not llm.configured():
        return None
    try:
        reply = await llm.complete([{"role": "system", "content": REVIEW_RULES}, {"role": "user", "content": prompt}], [])
    except llm.AgentLLMError:
        return None
    review = _parse(reply.content)
    if review is None:
        logger.warning("AI review wasn't valid JSON")
    return review


def _job_brief(job: Job | None) -> str:
    if not job:
        return "Job: (unknown)"
    return (f"Job: {job.title}\nRequired skills: {', '.join(job.required_skills) or 'none listed'}\n"
            f"Minimum experience: {job.min_experience_years} years\nDescription: {job.description[:1500]}")


async def review_assessment(job: Job | None, title: str, instructions: str, submission: str) -> Review | None:
    return await _review(
        f"{_job_brief(job)}\n\nTask: {title}\nInstructions:\n{instructions[:3000]}\n\n"
        f"Applicant's submission:\n{submission[:8000] or '(empty)'}"
    )


async def review_video_answers(job: Job | None, questions: list[str], transcripts: list[str]) -> Review | None:
    qa = "\n\n".join(f"Q{i + 1}: {q}\nAnswer (transcript): {t or '(no answer)'}"
                     for i, (q, t) in enumerate(zip(questions, transcripts, strict=False)))
    return await _review(f"{_job_brief(job)}\n\nVideo screening answers, transcribed:\n\n{qa[:9000]}")


async def transcribe(data: bytes, filename: str, content_type: str, language: str | None = None) -> str:
    """Speech to text with Whisper on the same OpenAI-compatible provider. Empty string if unavailable.
    `language` ("en", "ne") matters: without it Whisper often mistakes Nepali for another language."""
    s = get_settings()
    api_key = s.agent_llm_api_key or s.groq_api_key
    if not api_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                f"{s.agent_llm_base_url.rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, data, content_type)},
                data={"model": s.transcription_model, "response_format": "text",
                      **({"language": language} if language else {})},
            )
        res.raise_for_status()
        text = res.text.strip()
        # Whisper invents filler ("you", "Thank you.") from silence or noise; that isn't an answer.
        return text if len(text.split()) >= 3 else ""
    except httpx.HTTPError as exc:
        detail = exc.response.text[:200] if isinstance(exc, httpx.HTTPStatusError) else str(exc)
        logger.warning("Transcription failed: %s", detail)
        return ""


DEVANAGARI = re.compile(r"[ऀ-ॿ]")


async def english_version(transcript: str) -> str | None:
    """An English translation for HR when the answer was spoken in Nepali (or mixed); None when it's already
    English or no model is available."""
    if not transcript or not DEVANAGARI.search(transcript) or not llm.configured():
        return None
    try:
        reply = await llm.complete([
            {"role": "system", "content": "Translate this spoken interview answer from Nepali (possibly mixed with "
                                          "English) into natural English. Keep the meaning exactly; add nothing. "
                                          "Output only the translation."},
            {"role": "user", "content": transcript[:6000]},
        ], [])
    except llm.AgentLLMError:
        return None
    return reply.content.strip() or None
