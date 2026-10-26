from datetime import timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.entities import Application, ApplicationStatus, Interview, Job, OnboardingTask, User, UserRole
from shared.schemas.common import AnalyticsSummary


async def get_hiring_analytics(db: AsyncSession, organization_id: int) -> AnalyticsSummary:
    jobs = (await db.execute(
        select(Job.status, func.count()).where(Job.organization_id == organization_id).group_by(Job.status)
    )).all()
    job_counts = {status: count for status, count in jobs}

    status_rows = (await db.execute(
        select(Application.status, func.count())
        .where(Application.organization_id == organization_id)
        .group_by(Application.status)
    )).all()
    funnel: dict[str, int] = {s.value: 0 for s in ApplicationStatus}
    for status, count in status_rows:
        funnel[status.value] = count

    source_rows = (await db.execute(
        select(Application.source, func.count())
        .where(Application.organization_id == organization_id)
        .group_by(Application.source)
    )).all()
    total_apps = sum(funnel.values())
    source_effectiveness = {
        source or "other": round(100 * count / total_apps) for source, count in source_rows
    } if total_apps else {}

    avg_match = (await db.execute(
        select(func.avg(Application.match_score)).where(Application.organization_id == organization_id)
    )).scalar()

    hired = (await db.execute(
        select(Application.created_at, Application.hired_at).where(
            Application.organization_id == organization_id, Application.hired_at.is_not(None)
        )
    )).all()
    deltas = [(_utc(h) - _utc(c)).days for c, h in hired if c and h]
    avg_tth = sum(deltas) / len(deltas) if deltas else None

    return AnalyticsSummary(
        total_jobs=sum(job_counts.values()),
        open_jobs=job_counts.get("open", 0),
        total_applications=total_apps,
        avg_time_to_hire_days=avg_tth,
        avg_match_score=round(avg_match, 3) if avg_match is not None else None,
        funnel=funnel,
        source_effectiveness=source_effectiveness,
    )


async def get_org_metrics(db: AsyncSession, organization_id: int) -> dict[str, Any]:
    """Live counts that feed the AI dashboards (previously hardcoded)."""
    async def count(stmt) -> int:
        return (await db.execute(stmt)).scalar() or 0

    summary = await get_hiring_analytics(db, organization_id)
    employees = await count(
        select(func.count()).select_from(User).where(
            User.organization_id == organization_id,
            User.role.in_([UserRole.EMPLOYEE, UserRole.RECRUITER, UserRole.ADMIN]),
            User.is_active,
        )
    )
    pending_interviews = await count(
        select(func.count()).select_from(Interview).where(
            Interview.organization_id == organization_id, Interview.status == "scheduled"
        )
    )
    active_onboardings = await count(
        select(func.count()).select_from(OnboardingTask).where(
            OnboardingTask.organization_id == organization_id, OnboardingTask.status == "in_progress"
        )
    )
    hired = summary.funnel.get(ApplicationStatus.HIRED.value, 0)
    offers = summary.funnel.get(ApplicationStatus.OFFER.value, 0) + hired
    return {
        "total_applications": summary.total_applications,
        "pending_interviews": pending_interviews,
        "recent_hires": hired,
        "avg_time_to_hire_days": summary.avg_time_to_hire_days,
        "offer_acceptance_rate": round(hired / offers, 2) if offers else None,
        "headcount": employees,
        "active_onboardings": active_onboardings,
    }


def _utc(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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
