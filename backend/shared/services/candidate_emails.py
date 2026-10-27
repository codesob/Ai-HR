"""Emails that keep applicants and the hiring company informed at every step."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.config import get_settings
from shared.models.entities import Organization, User, UserRole
from shared.services.events import publish_notification


def first_name(name: str | None) -> str:
    return (name or "").split()[0] if (name or "").strip() else "there"


def _account_link() -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/candidate"


async def company_name(db: AsyncSession, organization_id: int) -> str:
    org = await db.get(Organization, organization_id)
    return org.name if org else "The hiring team"


def stage_message(stage: str, name: str, job: str, company: str) -> tuple[str, str] | None:
    """Subject and body for an applicant when their application moves to `stage`; None when another email covers it
    (a task, a video screen, an interview booking or the onboarding welcome)."""
    hi = f"Hi {first_name(name)},\n\n"
    sign = f"\n\nYou can follow your application any time: {_account_link()}\n\n{company}"
    return {
        "applied": (f"We got your application for {job}",
                    f"{hi}Thanks for applying for {job} at {company}. Every application is read, and we'll email you "
                    f"as soon as there's news.{sign}"),
        "screening": (f"Your application for {job} is being reviewed",
                      f"{hi}Good news: your application for {job} has moved to the next step and the team is "
                      f"reviewing it now.{sign}"),
        "interview": (f"{company} would like to interview you",
                      f"{hi}We'd like to interview you for {job}. We'll send you a time and a video link shortly.{sign}"),
        "offer": (f"Good news about {job}",
                  f"{hi}We'd like to offer you the {job} role at {company}. We'll be in touch with the details very "
                  f"soon.{sign}"),
        "rejected": (f"Your application for {job}",
                     f"{hi}Thank you for applying for {job}. After reviewing every application we've decided to move "
                     f"forward with other candidates. We'll keep your details on file for future roles.\n\n{company}"),
    }.get(stage)


async def email_applicant(db: AsyncSession, organization_id: int, to: str, subject: str, body: str,
                          event_type: str, payload: dict) -> None:
    await publish_notification(db, organization_id=organization_id, recipient=to, channel="email", subject=subject,
                               body=body, event_type=event_type, payload=payload, send_now=True)


async def email_hiring_team(db: AsyncSession, organization_id: int, subject: str, body: str,
                            event_type: str, payload: dict) -> None:
    """Admins and recruiters of the company."""
    team = (await db.execute(select(User.email).where(
        User.organization_id == organization_id, User.is_active,
        User.role.in_([UserRole.ADMIN, UserRole.RECRUITER]),
    ))).scalars().all()
    for email in team:
        await publish_notification(db, organization_id=organization_id, recipient=email, channel="email",
                                   subject=subject, body=body, event_type=event_type, payload=payload, send_now=True)
