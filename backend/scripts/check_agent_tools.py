"""Smoke-test every HR agent tool against the real database, then roll everything back.

    docker compose exec chatbot-rag-assistant-svc python scripts/check_agent_tools.py [org-slug]

Calls each tool the way the agent would (no language model involved), prints what happened, and also
approves one proposal of each kind to prove the approval path. Nothing is kept: the transaction is rolled back.
Emails the tools send are real (they go to whatever SMTP server is configured, e.g. Mailpit).
"""

import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from shared.db.session import AsyncSessionLocal
from shared.models.agent import AgentAction
from shared.models.entities import Application, ApplicationStatus, OnboardingTask, Organization, User, UserRole
from shared.models.leave import LeaveRequest
from shared.services.agent.runner import call_tool, decide_action
from shared.services.agent.tools import REGISTRY, Ctx


def show(name: str, result: dict) -> bool:
    if "error" in result:
        print(f"  FAIL  {name}: {result['error']}")
        return False
    if result.get("waiting_for_approval"):
        print(f"  OK    {name}: proposed → {result['summary']}")
        return True
    body = json.dumps(result.get("result"), default=str)
    print(f"  OK    {name}: {body[:150]}{'…' if len(body) > 150 else ''}")
    return True


async def main(slug: str) -> int:
    failures = 0
    tested: set[str] = set()
    async with AsyncSessionLocal() as db:
        org = (await db.execute(select(Organization).where(Organization.slug == slug))).scalar_one()
        people = {u.role: u for u in (await db.execute(
            select(User).where(User.organization_id == org.id, User.is_active).order_by(User.id)
        )).scalars()}
        admin, employee = people[UserRole.ADMIN], people[UserRole.EMPLOYEE]
        candidate = people.get(UserRole.CANDIDATE)
        staff = Ctx(db=db, organization_id=org.id, user=admin)

        async def run(ctx: Ctx, name: str, args: dict) -> dict:
            nonlocal failures
            tested.add(name)
            result = await call_tool(ctx, None, name, args)
            failures += not show(name, result)
            return result

        print(f"HR manager tools ({admin.full_name}, {org.name})")
        work = (await run(staff, "get_workload", {})).get("result", {})
        job_id = next((j["job_id"] for j in work.get("open_jobs", [])), None)
        applicants = (await run(staff, "list_applicants", {"job_id": job_id})).get("result", {}).get("applicants", [])
        open_app = next((a for a in applicants if a["stage"] not in ("hired", "rejected")), None)
        await run(staff, "read_resume", {"application_id": (open_app or applicants[0])["application_id"]})
        await run(staff, "list_team", {})
        await run(staff, "search_policies", {"query": "How many days of annual leave do I get?"})
        leave = (await run(staff, "list_time_off_requests", {})).get("result", [])

        app = (await db.execute(select(Application).where(
            Application.organization_id == org.id,
            Application.status.in_([ApplicationStatus.APPLIED, ApplicationStatus.SCREENING, ApplicationStatus.ASSESSMENT]),
        ))).scalars().first()
        await run(staff, "move_candidate", {"application_id": app.id, "stage": "screening"})
        proposal = await run(staff, "move_candidate", {"application_id": app.id, "stage": "offer", "reason": "smoke test"})
        when = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=14, minute=0, second=0, microsecond=0)
        await run(staff, "schedule_interview", {"application_id": app.id, "start": when.isoformat()})
        await run(staff, "send_message", {"to_email": employee.email, "subject": "Smoke test",
                                          "body": "Checking the HR agent can email you. Ignore this."})

        if leave:
            await run(staff, "decide_leave", {"leave_id": leave[0]["leave_id"], "decision": "decline", "reason": "test"})
        else:
            print("  SKIP  decide_leave: no time-off requests waiting")
        last_month = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        tested.add("run_payroll")
        payroll = await call_tool(staff, None, "run_payroll", {"month": last_month, "reason": "smoke test"})
        if "already paid" in payroll.get("error", ""):
            print(f"  OK    run_payroll: refused, {payroll['error']}")
        else:
            failures += not show("run_payroll", payroll)

        hire = await run(staff, "start_onboarding", {"name": "Smoke Test", "email": "smoke-hire@example.com", "role": "Tester"})
        onboarding = await run(staff, "list_onboarding", {})
        record = next(o for o in onboarding["result"] if o["onboarding_id"] == hire["result"]["onboarding_id"])
        await run(staff, "complete_onboarding_task", {"onboarding_id": record["onboarding_id"],
                                                      "task_id": record["tasks"][0]["task_id"]})

        print(f"\nEmployee self-service ({employee.full_name})")
        me = Ctx(db=db, organization_id=org.id, user=employee)
        await run(me, "my_time_off", {})
        start = date.today() + timedelta(days=150)
        await run(me, "request_time_off", {"leave_type": "annual", "start_date": str(start),
                                           "end_date": str(start + timedelta(days=1))})
        await run(me, "my_payslips", {})
        blocked = await call_tool(me, None, "list_team", {})
        ok = "error" in blocked
        failures += not ok
        print(f"  {'OK  ' if ok else 'FAIL'}  employees can't use HR tools (list_team → {blocked.get('error', 'ALLOWED')})")

        if candidate:
            print(f"\nApplicant self-service ({candidate.full_name})")
            await run(Ctx(db=db, organization_id=org.id, user=candidate), "my_applications", {})

        print("\nApprovals (a person says yes)")
        for action in (await db.execute(select(AgentAction).where(
            AgentAction.organization_id == org.id, AgentAction.status == "proposed"
        ))).scalars().all():
            if action.tool == "move_candidate" and action.args.get("stage") == "offer" and action.reason != "smoke test":
                continue
            done = await decide_action(db, action, admin, approve=True)
            ok = done.status == "executed"
            failures += not ok
            print(f"  {'OK  ' if ok else 'FAIL'}  approve “{action.summary}” → {done.status} {json.dumps(done.result, default=str)[:110]}")

        # What actually changed in the database before rollback.
        await db.refresh(app)
        print(f"\nAfter approvals: application {app.id} is '{app.status.value}'", end="")
        if leave:
            lv = await db.get(LeaveRequest, leave[0]["leave_id"])
            print(f"; leave {lv.id} is '{lv.status.value}'", end="")
        hires = (await db.execute(select(OnboardingTask).where(OnboardingTask.employee_email == "smoke-hire@example.com"))).scalars().all()
        print(f"; smoke-test hire has {sum(t['completed'] for t in hires[0].tasks)} task(s) done")
        assert proposal.get("waiting_for_approval"), "offers must wait for approval"

        untested = set(REGISTRY) - tested
        print(f"\nTools exercised: {len(tested)} of {len(REGISTRY)}" + (f" (not run: {', '.join(sorted(untested))})" if untested else ""))
        await db.rollback()
        print("Rolled back; demo data unchanged.")
    print("ALL GOOD" if failures == 0 else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "demo")))
