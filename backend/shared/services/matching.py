from typing import Any

from shared.schemas.common import MatchExplanation, ParsedResume
from shared.services.embeddings import cosine_similarity, embed_text


def _skill_overlap(candidate_skills: list[str], required: list[str]) -> tuple[list[str], list[str], float]:
    cand_norm = {s.lower().strip() for s in candidate_skills}
    req_norm = {s.lower().strip() for s in required}
    if not req_norm:
        return [], [], 1.0
    matched = [s for s in required if s.lower().strip() in cand_norm]
    missing = [s for s in required if s.lower().strip() not in cand_norm]
    overlap = len(matched) / len(req_norm)
    return matched, missing, overlap


def compute_match(
    resume: ParsedResume,
    job_description: str,
    required_skills: list[str],
    min_experience: float,
    resume_text: str | None = None,
) -> MatchExplanation:
    resume_blob = resume_text or " ".join(
        [resume.summary or "", " ".join(resume.skills), resume.education or ""]
    )
    job_blob = f"{job_description} {' '.join(required_skills)}"

    resume_vec = embed_text(resume_blob[:8000])
    job_vec = embed_text(job_blob[:8000])
    semantic = cosine_similarity(resume_vec, job_vec)

    matched, missing, skill_overlap = _skill_overlap(resume.skills, required_skills)
    skill_gap_score = round(1.0 - skill_overlap, 3)

    if min_experience <= 0:
        experience_fit = 1.0
    else:
        experience_fit = min(1.0, resume.experience_years / min_experience)

    match_score = round(
        0.45 * semantic + 0.35 * skill_overlap + 0.20 * experience_fit,
        3,
    )
    confidence = round(min(1.0, 0.5 + 0.5 * (len(resume.skills) / max(len(required_skills), 1))), 3)

    explanation_parts = [
        f"Semantic similarity to job: {semantic:.0%}.",
        f"Skills matched: {', '.join(matched) or 'none'}.",
    ]
    if missing:
        explanation_parts.append(f"Skill gaps: {', '.join(missing)}.")
    explanation_parts.append(
        f"Experience: {resume.experience_years} years (required {min_experience})."
    )

    return MatchExplanation(
        match_score=match_score,
        skill_gap_score=skill_gap_score,
        experience_fit=round(experience_fit, 3),
        confidence_score=confidence,
        matched_skills=matched,
        missing_skills=missing,
        semantic_similarity=round(semantic, 3),
        explanation=" ".join(explanation_parts),
    )


def rank_applications(applications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Learning-to-rank style heuristic scoring for MVP."""
    for app in applications:
        base = app.get("match_score") or 0
        parsed = app.get("parsed_data") or {}
        cert_bonus = min(0.1, len(parsed.get("certifications", [])) * 0.02)
        skill_bonus = min(0.15, len(parsed.get("skills", [])) * 0.01)
        exp_bonus = min(0.1, (parsed.get("experience_years") or 0) * 0.02)
        app["rank_score"] = round(min(1.0, base + cert_bonus + skill_bonus + exp_bonus), 3)
    return sorted(applications, key=lambda x: x.get("rank_score", 0), reverse=True)
