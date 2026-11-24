"""Runs the HR agent on every active workspace every AGENT_SCHEDULE_MINUTES (off when 0)."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.core.config import get_settings
from shared.db.session import AsyncSessionLocal
from shared.models.agent import AgentRun
from shared.models.entities import Organization
from shared.services.agent import llm
from shared.services.agent.runner import DAILY_WORK, run_agent

logger = logging.getLogger(__name__)
_task: asyncio.Task | None = None


async def run_due_workspaces(every: timedelta) -> int:
    """One pass: workspaces without a scheduled run in the last interval get one. Returns how many ran."""
    async with AsyncSessionLocal() as db:
        org_ids = (await db.execute(select(Organization.id).where(Organization.is_active))).scalars().all()
    ran = 0
    for org_id in org_ids:
        async with AsyncSessionLocal() as db:
            recent = (await db.execute(
                select(AgentRun.id).where(
                    AgentRun.organization_id == org_id, AgentRun.trigger == "schedule",
                    AgentRun.created_at >= datetime.now(timezone.utc) - every,
                )
            )).first()
            if recent:
                continue
            try:
                await run_agent(db, organization_id=org_id, user=None, instruction=DAILY_WORK, trigger="schedule")
                await db.commit()
                ran += 1
            except Exception:
                await db.rollback()
                logger.exception("Scheduled agent run failed", extra={"organization_id": org_id})
    return ran


async def _loop(every: timedelta) -> None:
    while True:
        await asyncio.sleep(every.total_seconds())
        try:
            await run_due_workspaces(every)
        except Exception:
            logger.exception("Agent schedule pass failed")


async def start_schedule() -> None:
    global _task
    minutes = get_settings().agent_schedule_minutes
    if minutes <= 0 or not llm.configured():
        return
    _task = asyncio.create_task(_loop(timedelta(minutes=minutes)))
    logger.info("HR agent schedule on", extra={"minutes": minutes})


async def stop_schedule() -> None:
    if _task:
        _task.cancel()
