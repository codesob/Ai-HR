"""Events that start the HR agent without anyone asking."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.core.config import get_settings
from shared.db.session import AsyncSessionLocal
from shared.models.entities import Application
from shared.services.agent import llm
from shared.services.agent.runner import run_agent

logger = logging.getLogger(__name__)


async def screen_new_application(organization_id: int, application_id: int) -> None:
    """Runs after someone applies: the agent reads the resume and moves the application forward, proposes a
    rejection, or leaves it for a person. Best-effort; the application already exists either way."""
    if not get_settings().agent_screen_new_applications or not llm.configured():
        return
    async with AsyncSessionLocal() as db:
        try:
            app = (await db.execute(
                select(Application).where(Application.id == application_id, Application.organization_id == organization_id)
                .options(selectinload(Application.job), selectinload(Application.candidate))
            )).scalar_one_or_none()
            if not app:
                return
            who = app.candidate.full_name if app.candidate else "Someone"
            job = app.job.title if app.job else "a job"
            await run_agent(
                db, organization_id=organization_id, user=None, trigger="application",
                instruction=(
                    f"{who} just applied for {job} (application {application_id}). Read their resume with read_resume "
                    "and compare it with the job. If they clearly meet the requirements, move them to screening. If "
                    "they clearly don't, propose a rejection naming the requirement they miss. If there's no resume, "
                    "email them (send_message) asking them to upload one in their account so we can review their "
                    "application. If it's unclear, leave it for a person and say why. Only handle this one application."
                ),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Screening a new application failed", extra={"application_id": application_id})
