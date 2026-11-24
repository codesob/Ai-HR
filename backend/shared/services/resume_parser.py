import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from docx import Document

from shared.schemas.common import ParsedResume

SKILL_KEYWORDS = {
    "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#",
    "react", "next.js", "nextjs", "node.js", "nodejs", "fastapi", "django",
    "flask", "sql", "postgresql", "mongodb", "redis", "docker", "kubernetes",
    "aws", "azure", "gcp", "pytorch", "tensorflow", "machine learning", "ml",
    "deep learning", "nlp", "rag", "llm", "langchain", "git", "ci/cd",
    "agile", "scrum", "rest", "graphql", "microservices", "linux",
}

EDUCATION_PATTERNS = [
    r"(?:B\.?S\.?c?|Bachelor(?:'s)?)\s+(?:of\s+)?[\w\s]+",
    r"(?:M\.?S\.?c?|Master(?:'s)?)\s+(?:of\s+)?[\w\s]+",
    r"(?:Ph\.?D|Doctorate)\s+[\w\s]+",
    r"(?:B\.?Tech|M\.?Tech|MBA)\s+[\w\s]*",
]

CERT_PATTERNS = [
    r"AWS\s+Certified[\w\s]*",
    r"Azure\s+[\w\s]+",
    r"Google\s+Cloud[\w\s]*",
    r"PMP|CISSP|CKA|CKAD",
]


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in (".docx", ".doc"):
        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = re.search(r"\+?[\d\s().-]{10,}", text)
    return match.group(0).strip() if match else None


def _extract_name(text: str) -> str | None:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first) < 60 and "@" not in first:
        return first
    return None


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found = {s for s in SKILL_KEYWORDS if s in lower}
    # Title-case common tech names
    display = []
    for skill in sorted(found):
        if skill in ("nextjs", "nodejs"):
            display.append(skill.replace("js", ".js").title())
        elif skill == "ci/cd":
            display.append("CI/CD")
        else:
            display.append(skill.title() if len(skill) > 3 else skill.upper())
    return display


def _extract_experience_years(text: str) -> float:
    patterns = [
        r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
        r"experience[:\s]+(\d+)\+?\s*years?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return float(m.group(1))
    # Count year ranges like 2020-2023
    ranges = re.findall(r"(20\d{2})\s*[-\u2013]\s*(20\d{2}|present|current)", text, re.I)
    if ranges:
        total = 0
        for start, end in ranges:
            end_year = 2026 if end.lower() in ("present", "current") else int(end)
            total += max(0, end_year - int(start))
        return min(float(total), 30.0)
    return 0.0


def _extract_education(text: str) -> str | None:
    for pat in EDUCATION_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0).strip()
    return None


def _extract_certifications(text: str) -> list[str]:
    certs = []
    for pat in CERT_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            certs.append(m.group(0).strip())
    return list(dict.fromkeys(certs))


def _extract_work_experience(text: str) -> list[dict[str, Any]]:
    experiences = []
    blocks = re.split(r"\n(?=[A-Z][\w\s/&-]+\s*(?:\||at\s|@|\d{4}))", text)
    for block in blocks[:8]:
        if len(block) > 40 and any(kw in block.lower() for kw in ("engineer", "developer", "manager", "analyst", "intern")):
            title_match = re.match(r"^(.{5,80})", block.strip())
            experiences.append({
                "title": title_match.group(1).strip() if title_match else "Role",
                "snippet": block[:300],
            })
    return experiences[:5]


def parse_resume_text(text: str) -> ParsedResume:
    return ParsedResume(
        name=_extract_name(text),
        email=_extract_email(text),
        phone=_extract_phone(text),
        skills=_extract_skills(text),
        experience_years=_extract_experience_years(text),
        education=_extract_education(text),
        certifications=_extract_certifications(text),
        work_experience=_extract_work_experience(text),
        projects=[],
        summary=text[:500] if text else None,
    )


async def parse_resume_file(file_path: Path) -> ParsedResume:
    text = extract_text_from_file(file_path)
    return parse_resume_text(text)


AI_PROMPT = """Read this resume and reply with JSON only, no prose:
{"name": str|null, "skills": [str], "experience_years": number, "education": str|null,
 "certifications": [str], "work_experience": [{"title": str, "company": str, "years": str}], "summary": str}
Rules: skills are concrete professional skills and tools in any field (e.g. Figma, User Research, Bookkeeping, Python),
named in English even when written in Nepali, at most 25, no soft-skill filler. experience_years is total paid
professional experience. education is the highest degree with institution, in English. summary is two plain English
sentences about their work. Leave out anything not in the resume; never guess."""


async def parse_resume_smart(text: str) -> ParsedResume:
    """Pattern parsing, improved by the language model when one is configured. Contact details always come from
    the patterns, never the model."""
    import json

    from shared.services.agent import llm

    base = parse_resume_text(text)
    if not text.strip() or not llm.configured():
        return base
    try:
        reply = await llm.complete([{"role": "system", "content": AI_PROMPT}, {"role": "user", "content": text[:12000]}], [])
        found = re.search(r"\{.*\}", reply.content, re.DOTALL)
        data = json.loads(found.group(0)) if found else {}
    except (llm.AgentLLMError, ValueError):
        return base
    skills = [str(s).strip() for s in data.get("skills") or [] if str(s).strip()][:25]
    try:
        years = float(data.get("experience_years") or 0)
    except (TypeError, ValueError):
        years = 0.0
    return base.model_copy(update={
        "name": data.get("name") or base.name,
        "skills": list(dict.fromkeys(skills + base.skills)) or base.skills,
        "experience_years": years if 0 < years <= 60 else base.experience_years,
        "education": data.get("education") or base.education,
        "certifications": [str(c) for c in data.get("certifications") or []] or base.certifications,
        "work_experience": [w for w in data.get("work_experience") or [] if isinstance(w, dict)] or base.work_experience,
        "summary": data.get("summary") or base.summary,
    })
