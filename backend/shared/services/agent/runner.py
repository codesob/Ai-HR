"""The HR agent loop: the model looks around, calls tools, and keeps going until the work is done."""

import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.config import get_settings
from shared.models.agent import AgentAction, AgentRun
from shared.models.entities import Organization, User, UserRole
from shared.services.agent import llm
from shared.services.events import publish_notification
from shared.services.agent.tools import REGISTRY, Ctx, NeedsApproval, ToolError, tools_for

logger = logging.getLogger(__name__)

DAILY_WORK = (
    "Do today's HR work for this company. Check the workload, then: screen new applicants (read each resume; move "
    "clear fits to screening; propose rejections only for clear mismatches, with the reason), decide waiting "
    "time-off requests, review submitted tasks and video screens (propose pass or fail with decide_screening, "
    "using the AI review and your own reading), check new hires' onboarding checklists and nudge anyone with tasks still open after a few "
    "days, and if last month's payroll hasn't been run, propose running it. Finish with a short summary of what you "
    "did and what is waiting for a person."
)

STAFF_PROMPT = """You are the HR team for {company}. You do the work, not just advise: use the tools to act.

How you work:
- Look before you act (get_workload, list_applicants, list_time_off_requests). Never invent ids, names or numbers.
- Act on routine work yourself. Some actions are sent to a person to approve; that's expected, carry on with the rest.
- Every hiring decision must rest on the job's stated requirements: skills and experience. Never consider age,
  gender, ethnicity, religion, disability, family status or anything else unrelated to the work.
- Read the resume (read_resume) before moving or rejecting anyone. Never reject only because a score is low;
  say which requirement they don't meet. A missing resume is never a reason to reject: email the person
  (send_message) asking them to upload one, and leave the application open.
- Time off: approve unless there's a concrete problem (not enough days left, a clash the team can't cover).
  If it can't be approved automatically, still ask to approve it and say what's unusual. A missing policy is not
  a reason to decline; leave that call to the person.
- When a person asks you something, answer from tools (search_policies for policy). If you can't find it, say so.
- Language: people may write in English, in Nepali (Devanagari), in romanized Nepali ("malai bida chahiyo"),
  or a mix. Understand all of them and reply in the language and script they used. Tool arguments, search
  queries and emails to others stay in English unless the person asks otherwise.
- Today is {today}. You act for {who}.
- End with a short summary in plain text, no markdown (no **, #, or tables). First "Done:" with one "- " line per
  change that actually happened. Then "Waiting for your OK:" with one "- " line per proposal a tool told you is
  waiting for approval; nothing else goes there (suggestions belong in a plain sentence). Never describe a
  proposal as done (say "Proposed rejecting …", not "Rejected …"). If you only answered a question and changed
  nothing, just answer; leave out both headings."""

SELF_SERVICE_PROMPT = """You are the HR team for {company}, talking with {who} ({role}).
You can look up policies and act on this person's own HR matters with the tools. Use them; don't just explain.
- For policy questions, call search_policies and answer from what it returns; mention which policy.
- To book time off, make sure you have the type and exact dates, then call request_time_off.
- You can only see and change this person's own records. For anything else, say HR will follow up.
- They may write in English, Nepali (Devanagari), romanized Nepali, or a mix. Reply in the language and script
  they used. Policy search queries go in English (translate the question first); quote the policy in their language.
- Today is {today}. Be brief and friendly. Plain text only, no markdown (no **, #, or tables)."""


class ChatTurn(BaseModel):
    role: str
    content: str


def _summarize(result: object) -> str:
    text = json.dumps(result, default=str)
    return text if len(text) <= 3000 else text[:3000] + "…(truncated)"


# The argument that says what a proposal is about.
TARGET_ARG = {"move_candidate": "application_id", "decide_leave": "leave_id", "run_payroll": "month", "decide_screening": "id"}


async def _open_proposal(ctx: Ctx, tool: str, args: dict) -> AgentAction | None:
    key = TARGET_ARG.get(tool)
    if not key:
        return None
    pending = (await ctx.db.execute(
        select(AgentAction).where(
            AgentAction.organization_id == ctx.organization_id, AgentAction.tool == tool,
            AgentAction.status == "proposed",
        )
    )).scalars().all()
    return next((a for a in pending if a.args.get(key) == args.get(key)), None)


async def call_tool(ctx: Ctx, run: AgentRun | None, name: str, args: dict) -> dict:
    """Run one tool call for the model and return what it should see. Never raises."""
    t = REGISTRY.get(name)
    if not t or ctx.role not in t.roles:
        return {"error": f"There is no tool called {name} available to you."}
    reason = str(args.get("reason", "") or "")
    # Models sometimes add arguments a tool doesn't take; drop them rather than spend a turn on the error.
    args = {k: v for k, v in args.items() if k in t.params}
    try:
        # A savepoint per call: a failing tool can't leave half its changes behind.
        async with ctx.db.begin_nested():
            if t.approval and not ctx.approved:
                # Let the handler validate and describe the change first.
                await t.handler(ctx, **args)
                return {"error": f"{name} must be approved by a person."}
            return {"ok": True, "result": await t.handler(ctx, **args)}
    except NeedsApproval as wait:
        # One open proposal per thing: a newer idea about the same candidate, request or month replaces the old one.
        action = await _open_proposal(ctx, name, args)
        if action is None:
            action = AgentAction(organization_id=ctx.organization_id, tool=name)
            ctx.db.add(action)
        action.run_id = run.id if run else None
        action.args, action.summary, action.reason = args, wait.summary[:512], reason
        await ctx.db.flush()
        return {"ok": True, "waiting_for_approval": True, "action_id": action.id, "summary": wait.summary}
    except ToolError as exc:
        return {"error": str(exc)}
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception:
        logger.exception("Agent tool %s failed", name)
        return {"error": f"{name} failed unexpectedly; nothing was changed."}


async def run_agent(
    db: AsyncSession,
    *,
    organization_id: int,
    user: User | None,
    instruction: str,
    trigger: str,
    history: list[ChatTurn] | None = None,
) -> AgentRun:
    settings = get_settings()
    org = await db.get(Organization, organization_id)
    role = user.role if user else UserRole.ADMIN
    staff = role in (UserRole.ADMIN, UserRole.RECRUITER)
    today = datetime.now(timezone.utc).strftime("%A %d %B %Y")
    who = user.full_name if user else "the HR manager (scheduled run)"
    system = (STAFF_PROMPT if staff else SELF_SERVICE_PROMPT).format(
        company=org.name if org else "this company", today=today, who=who, role=role.value,
    )

    run = AgentRun(organization_id=organization_id, user_id=user.id if user else None, trigger=trigger,
                   instruction=instruction[:4000], steps=[])
    db.add(run)
    await db.flush()

    ctx = Ctx(db=db, organization_id=organization_id, user=user)
    specs = [t.spec() for t in tools_for(role)]
    messages: list[dict] = [{"role": "system", "content": system}]
    for turn in (history or [])[-10:]:
        if turn.role in ("user", "assistant") and turn.content:
            messages.append({"role": turn.role, "content": turn.content[:4000]})
    messages.append({"role": "user", "content": instruction})

    steps: list[dict] = []
    reply = ""
    try:
        for _ in range(settings.agent_max_steps):
            answer = await llm.complete(messages, specs)
            messages.append(answer.message)
            if not answer.tool_calls:
                reply = answer.content.strip()
                break
            for call in answer.tool_calls:
                result = await call_tool(ctx, run, call.name, call.arguments)
                steps.append({"tool": call.name, "args": call.arguments, "result": result})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": _summarize(result)})
        else:
            reply = "I stopped here to stay within my step limit. Ask me to carry on if there's more to do."
        run.status = "done"
    except llm.AgentLLMError as exc:
        run.status = "failed"
        reply = str(exc)

    # Models slip into markdown now and then; the app shows plain text.
    run.reply = reply.replace("**", "").strip() or "Done."
    run.steps = steps
    run.finished_at = datetime.now(timezone.utc)
    await db.flush()
    await notify_approvers(db, run)
    return run


async def notify_approvers(db: AsyncSession, run: AgentRun) -> int:
    """One email per run to the company's HR managers listing what waits for their OK. The person who started
    the run is skipped: they're looking at it in the app. Returns how many people were told."""
    waiting = (await db.execute(
        select(AgentAction).where(AgentAction.run_id == run.id, AgentAction.status == "proposed")
        .order_by(AgentAction.id)
    )).scalars().all()
    if not waiting:
        return 0
    admins = (await db.execute(
        select(User).where(User.organization_id == run.organization_id, User.role == UserRole.ADMIN, User.is_active)
    )).scalars().all()
    recipients = [a for a in admins if a.id != run.user_id]
    if not recipients:
        return 0

    link = f"{get_settings().frontend_url.rstrip('/')}/admin#approvals"
    items = "\n".join(f"- {a.summary}" + (f"\n  Why: {a.reason}" if a.reason else "") for a in waiting)
    subject = (f"Your OK needed: {waiting[0].summary}" if len(waiting) == 1
               else f"Your OK needed on {len(waiting)} things")
    for admin in recipients:
        await publish_notification(
            db, organization_id=run.organization_id, recipient=admin.email, channel="email",
            subject=subject[:255],
            body=(f"Hi {admin.full_name.split()[0]},\n\nThe HR agent has done the routine work and needs you to decide "
                  f"on {'this' if len(waiting) == 1 else 'these'}:\n\n{items}\n\nApprove or skip in one click: {link}\n\n"
                  "Nothing happens until you do.\n\nHR agent"),
            event_type="agent.approval_needed", payload={"run_id": run.id, "action_ids": [a.id for a in waiting]},
            send_now=True,
        )
    return len(recipients)


async def decide_action(db: AsyncSession, action: AgentAction, person: User, approve: bool) -> AgentAction:
    """A person approves (the change is made now, as them) or rejects a proposal."""
    action.decided_by_id = person.id
    action.decided_at = datetime.now(timezone.utc)
    if not approve:
        action.status = "rejected"
        await db.flush()
        return action
    t = REGISTRY.get(action.tool)
    ctx = Ctx(db=db, organization_id=action.organization_id, user=person, approved=True)
    if not t or person.role not in t.roles:
        action.status, action.result = "failed", {"error": "You don't have permission for this action."}
        await db.flush()
        return action
    try:
        async with db.begin_nested():
            result = await t.handler(ctx, **action.args)
        action.status, action.result = "executed", {"result": json.loads(json.dumps(result, default=str))}
    except (ToolError, NeedsApproval, ValueError) as exc:
        action.status, action.result = "failed", {"error": str(exc)}
    await db.flush()
    return action
