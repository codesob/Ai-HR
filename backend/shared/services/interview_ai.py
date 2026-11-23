"""AI help around a live interview: questions to ask before it, and notes from the transcript after it.

It works only from what was said and written. Never tone, face, accent or emotion (emotion recognition in hiring
is banned in the EU and is unreliable anyway). The interviewer makes the call.
"""

import json
import logging
import re

from shared.models.entities import Job
from shared.services.agent import llm
from shared.services.screening_ai import DEVANAGARI, _job_brief

logger = logging.getLogger(__name__)

FAIRNESS = ("Never consider or guess age, gender, ethnicity, accent, appearance, disability, religion, family status, "
            "tone of voice or emotion. The applicant may speak English, Nepali or a mix: judge what is said, never the "
            "language or fluency.")

# Free-tier providers cap tokens per minute, so long calls are condensed in pieces first.
DIRECT_LIMIT = 14000
CHUNK = 11000


def _json(content: str) -> dict | list | None:
    match = re.search(r"[\[{].*[\]}]", content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


async def _ask(system: str, user: str, max_tokens: int = 1400) -> str | None:
    if not llm.configured():
        return None
    try:
        return (await llm.complete([{"role": "system", "content": system}, {"role": "user", "content": user}], [],
                                   max_tokens=max_tokens)).content
    except llm.AgentLLMError:
        return None


async def prep_questions(job: Job | None, resume: str, screening: str) -> list[dict]:
    """6-8 questions for the interviewer, each with why it's worth asking; [] if no model."""
    reply = await _ask(
        "You help an interviewer prepare. Suggest 6 to 8 interview questions that test the job's requirements, "
        "dig into specific claims in the resume, and probe gaps or weak spots found in screening. Prefer questions "
        "about real past work ('Tell me about a time…', 'Walk me through…'). " + FAIRNESS + " Never ask about "
        "personal life. Reply with JSON only: [{\"question\": \"...\", \"why\": \"<one short sentence>\"}]",
        f"{_job_brief(job)}\n\nResume:\n{resume[:5000] or '(none uploaded)'}\n\nScreening so far:\n"
        f"{screening[:3000] or '(none)'}",
    )
    data = _json(reply or "")
    if not isinstance(data, list):
        return []
    return [{"question": str(q.get("question", ""))[:500], "why": str(q.get("why", ""))[:300]}
            for q in data if isinstance(q, dict) and q.get("question")][:8]


def format_transcript(lines: list[dict]) -> str:
    def stamp(at: float) -> str:
        return f"{int(at // 60):02d}:{int(at % 60):02d}"
    who = {"interviewer": "Interviewer", "candidate": "Applicant"}
    return "\n".join(f"[{stamp(line['at'])}] {who.get(line['speaker'], 'Speaker')}: {line['text']}" for line in lines)


def _chunks(text: str, size: int) -> list[str]:
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if current and len(current) + len(line) > size:
            parts.append(current)
            current = ""
        current += line
    return [*parts, current] if current else parts


async def english_transcript(text: str) -> str | None:
    """English version of a transcript that has Nepali in it, keeping the [mm:ss] Speaker: prefixes."""
    if not text or not DEVANAGARI.search(text):
        return None
    out = []
    for piece in _chunks(text, 5000):
        if not DEVANAGARI.search(piece):
            out.append(piece.rstrip("\n"))
            continue
        reply = await _ask("Translate this interview transcript from Nepali (possibly mixed with English) into "
                           "natural English. Keep every line's [mm:ss] Speaker: prefix exactly. Keep the meaning "
                           "exactly; add nothing. Output only the translated lines.", piece, max_tokens=3000)
        if reply is None:
            return None
        out.append(reply.strip())
    return "\n".join(out)


SUMMARY_RULES = (
    "You write notes for an interviewer from the transcript of their interview with a job applicant. Base every "
    "point on what the applicant actually said, and quote or closely paraphrase them as evidence. If they didn't "
    "cover something, say so; don't guess. The transcript comes from speech recognition, so expect some wrong words. "
    + FAIRNESS + " Write in English. Reply with JSON only:\n"
    '{"overview": "<2-3 sentences>", '
    '"skills": [{"skill": "<a required skill>", "evidence": "<what they said, or \'Not discussed\'>", '
    '"level": "strong" | "some" | "none"}], '
    '"strengths": ["..."], "concerns": ["..."], "follow_ups": ["<question to ask next time or check with references>"], '
    '"recommendation": "advance" | "unsure" | "decline"}'
)


async def summarize(job: Job | None, transcript: str) -> dict | None:
    """Structured interview notes, or None if there's no model or it didn't answer properly."""
    if len(transcript.split()) < 30:
        return {"overview": "The recording has too little speech to summarise. Check the audio, or write your own "
                            "notes in the scorecard.", "skills": [], "strengths": [], "concerns": [],
                "follow_ups": [], "recommendation": "unsure"}
    material = transcript
    if len(transcript) > DIRECT_LIMIT:
        notes = []
        for i, piece in enumerate(_chunks(transcript, CHUNK)):
            reply = await _ask(
                "Condense this part of an interview transcript into factual notes: what the applicant said about "
                "their experience, skills, decisions and results, with short quotes and [mm:ss] times. Note the "
                "interviewer's questions briefly. No judgements. " + FAIRNESS,
                f"Part {i + 1}:\n{piece}", max_tokens=900)
            if reply is None:
                return None
            notes.append(f"Part {i + 1} notes:\n{reply.strip()}")
        material = "\n\n".join(notes)
    reply = await _ask(SUMMARY_RULES, f"{_job_brief(job)}\n\nInterview:\n{material[:DIRECT_LIMIT]}", max_tokens=1800)
    data = _json(reply or "")
    if not isinstance(data, dict) or "overview" not in data:
        logger.warning("Interview summary wasn't valid JSON")
        return None

    def strings(key: str) -> list[str]:
        return [str(x)[:500] for x in data.get(key) or [] if x][:8]

    rec = str(data.get("recommendation", "")).lower()
    return {
        "overview": str(data["overview"])[:1500],
        "skills": [{"skill": str(s.get("skill", ""))[:100], "evidence": str(s.get("evidence", ""))[:600],
                    "level": s.get("level") if s.get("level") in ("strong", "some", "none") else "none"}
                   for s in data.get("skills") or [] if isinstance(s, dict) and s.get("skill")][:12],
        "strengths": strings("strengths"),
        "concerns": strings("concerns"),
        "follow_ups": strings("follow_ups"),
        "recommendation": rec if rec in ("advance", "unsure", "decline") else "unsure",
    }
