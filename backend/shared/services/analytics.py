from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.entities import Application, ApplicationStatus, Job
from shared.schemas.common import AnalyticsSummary


async def get_hiring_analytics(db: AsyncSession) -> AnalyticsSummary:
    jobs_result = await db.execute(select(Job))
    jobs = jobs_result.scalars().all()

    apps_result = await db.execute(select(Application))
    applications = apps_result.scalars().all()

    funnel: dict[str, int] = {s.value: 0 for s in ApplicationStatus}
    for app in applications:
        funnel[app.status.value] = funnel.get(app.status.value, 0) + 1

    match_scores = [a.match_score for a in applications if a.match_score is not None]
    avg_match = sum(match_scores) / len(match_scores) if match_scores else None

    hired = [a for a in applications if a.status == ApplicationStatus.HIRED]
    avg_tth = None
    if hired:
        deltas = [
            (datetime.now(timezone.utc) - a.created_at.replace(tzinfo=timezone.utc)).days
            for a in hired
            if a.created_at
        ]
        if deltas:
            avg_tth = sum(deltas) / len(deltas)

    return AnalyticsSummary(
        total_jobs=len(jobs),
        open_jobs=sum(1 for j in jobs if j.status == "open"),
        total_applications=len(applications),
        avg_time_to_hire_days=avg_tth,
        avg_match_score=round(avg_match, 3) if avg_match else None,
        funnel=funnel,
        diversity_placeholder={"gender_balance_index": 0.72, "note": "Connect HRIS for live DEI metrics"},
        source_effectiveness={"careers_page": 45, "linkedin": 32, "referral": 18, "other": 5},
    )


def pipeline_metrics(applications: list[dict[str, Any]]) -> dict[str, Any]:
    if not applications:
        return {"interview_to_offer": 0, "offer_acceptance": 0}
    interviews = sum(1 for a in applications if a.get("status") in ("interview", "offer", "hired"))
    offers = sum(1 for a in applications if a.get("status") in ("offer", "hired"))
    hired = sum(1 for a in applications if a.get("status") == "hired")
    return {
        "interview_to_offer_ratio": round(offers / max(interviews, 1), 2),
        "offer_acceptance_rate": round(hired / max(offers, 1), 2),
    }
