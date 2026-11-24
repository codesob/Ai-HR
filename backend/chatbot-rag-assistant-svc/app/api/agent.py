from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.agent import AgentAction, AgentRun
from shared.models.entities import User, UserRole
from shared.services.agent import llm
from shared.services.agent.runner import DAILY_WORK, ChatTurn, decide_action, run_agent

router = APIRouter(prefix="/agent", tags=["agent"])

hr_staff = require_roles(UserRole.ADMIN, UserRole.RECRUITER)


class AgentChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class AgentWork(BaseModel):
    instruction: str | None = Field(default=None, max_length=4000)


class StepOut(BaseModel):
    tool: str
    args: dict
    result: dict


class ActionOut(BaseModel):
    id: int
    tool: str
    summary: str
    reason: str
    status: str
    result: dict
    created_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: int
    trigger: str
    instruction: str
    status: str
    reply: str
    steps: list[StepOut]
    created_at: datetime
    proposed: list[ActionOut] = []

    model_config = {"from_attributes": True}


async def _with_proposals(db: AsyncSession, run: AgentRun) -> RunOut:
    proposed = (await db.execute(select(AgentAction).where(AgentAction.run_id == run.id))).scalars().all()
    out = RunOut.model_validate(run)
    out.proposed = [ActionOut.model_validate(a) for a in proposed]
    return out


@router.get("/status")
async def agent_status(_: User = Depends(require_user)):
    return {"configured": llm.configured()}


@router.post("/chat", response_model=RunOut)
async def chat_with_agent(
    payload: AgentChat, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    """Anyone signed in. Staff get the full HR toolset; everyone else acts only on their own records."""
    run = await run_agent(db, organization_id=user.organization_id, user=user, instruction=payload.message,
                          trigger="chat", history=payload.history)
    return await _with_proposals(db, run)


@router.post("/run", response_model=RunOut)
async def do_the_work(
    payload: AgentWork, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)
):
    run = await run_agent(db, organization_id=user.organization_id, user=user,
                          instruction=payload.instruction or DAILY_WORK, trigger="run")
    return await _with_proposals(db, run)


@router.get("/runs", response_model=list[RunOut])
async def recent_runs(db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)):
    runs = (await db.execute(
        select(AgentRun)
        .where(AgentRun.organization_id == user.organization_id, AgentRun.trigger != "chat")
        .order_by(AgentRun.created_at.desc()).limit(10)
    )).scalars().all()
    return [await _with_proposals(db, r) for r in runs]


@router.get("/actions", response_model=list[ActionOut])
async def list_actions(
    status: str = "proposed", db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)
):
    rows = (await db.execute(
        select(AgentAction)
        .where(AgentAction.organization_id == user.organization_id, AgentAction.status == status)
        .order_by(AgentAction.created_at.desc()).limit(50)
    )).scalars().all()
    return rows


async def _proposal(db: AsyncSession, action_id: int, user: User) -> AgentAction:
    action = (await db.execute(
        select(AgentAction).where(AgentAction.id == action_id, AgentAction.organization_id == user.organization_id)
    )).scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "proposed":
        raise HTTPException(status_code=409, detail=f"This was already {action.status}.")
    return action


@router.post("/actions/{action_id}/approve", response_model=ActionOut)
async def approve_action(
    action_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)
):
    return await decide_action(db, await _proposal(db, action_id, user), user, approve=True)


@router.post("/actions/{action_id}/reject", response_model=ActionOut)
async def reject_action(
    action_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(hr_staff)
):
    return await decide_action(db, await _proposal(db, action_id, user), user, approve=False)
