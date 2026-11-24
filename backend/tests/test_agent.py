"""The HR agent, driven by a scripted model so every step is deterministic."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from shared.db.session import AsyncSessionLocal
from shared.models.agent import AgentAction
from shared.models.entities import Application, Notification
from shared.models.leave import LeaveRequest
from shared.models.payroll import Payslip
from shared.services.agent import llm
from tests.conftest import bearer, service_client, signup
from tests.test_saas import JOB, make_candidate

API = "/api/v1"


class ScriptedModel:
    """Replays tool calls turn by turn and records which tools the agent offered."""

    def __init__(self, turns: list[list[tuple[str, dict]] | str]):
        self.turns = list(turns)
        self.offered: list[set[str]] = []
        self.seen: list[list[dict]] = []

    async def __call__(self, messages, tools):
        self.offered.append({t["function"]["name"] for t in tools})
        self.seen.append(messages)
        turn = self.turns.pop(0)
        if callable(turn):  # built from what the agent was told, e.g. a new application id
            turn = turn(messages)
        if isinstance(turn, str):
            return llm.LLMReply(content=turn, message={"role": "assistant", "content": turn})
        raw = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": "{}"}}
               for i, (n, _) in enumerate(turn)]
        return llm.LLMReply(
            content="",
            tool_calls=[llm.ToolCall(id=f"c{i}", name=n, arguments=a) for i, (n, a) in enumerate(turn)],
            message={"role": "assistant", "content": "", "tool_calls": raw},
        )


@pytest.fixture
def model(monkeypatch):
    monkeypatch.setattr(llm, "configured", lambda: True)

    def install(turns):
        m = ScriptedModel(turns)
        monkeypatch.setattr(llm, "complete", m)
        return m
    return install


@pytest.fixture
async def agent():
    client = service_client("chatbot-rag-assistant-svc")
    yield client
    await client.aclose()


async def _workspace(clients):
    gw, me = clients["api-gateway"], clients["matching-engine-svc"]
    admin = await signup(gw, "Acme", "a@acme.io")
    token = admin["access_token"]
    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(token))).json()
    apps = []
    for email in ("fit@acme.io", "nofit@acme.io"):
        cand = await make_candidate(gw, "acme", email)
        apps.append((await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand))).json()["id"])
    return admin, token, job, apps


async def _employee(gw, admin_token: str, email: str = "e@acme.io") -> str:
    invite = (await gw.post(f"{API}/users/invite", json={"email": email, "role": "employee"},
                            headers=bearer(admin_token))).json()
    return (await gw.post(f"{API}/auth/accept-invite", json={
        "token": invite["invite_url"].split("token=")[1], "full_name": "Emp", "password": "employee-pass-1",
    })).json()["access_token"]


async def _status(app_id: int) -> str:
    async with AsyncSessionLocal() as db:
        return (await db.get(Application, app_id)).status.value


async def test_agent_acts_on_routine_work_and_queues_big_decisions(clients, agent, model):
    admin, token, job, (fit, nofit) = await _workspace(clients)
    pay = clients["payroll-automation-svc"]
    await pay.put(f"{API}/payroll/profile", json={"user_id": admin["user"]["id"], "annual_base": 120000},
                  headers=bearer(token))
    last_month = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    model([
        [("get_workload", {})],
        [("move_candidate", {"application_id": fit, "stage": "screening", "reason": "Has every required skill"}),
         ("move_candidate", {"application_id": nofit, "stage": "rejected", "reason": "No Python or FastAPI"}),
         ("run_payroll", {"month": last_month, "reason": "Last month isn't paid yet"})],
        "Moved one applicant to screening; a rejection and payroll are waiting for you.",
    ])
    res = await agent.post(f"{API}/agent/run", json={}, headers=bearer(token))
    assert res.status_code == 200, res.text
    run = res.json()
    assert run["status"] == "done" and run["reply"].startswith("Moved one")
    assert run["steps"][0]["result"]["result"]["open_jobs"][0]["new_applicants"] == 2

    # Routine: done. Consequential: proposed, nothing changed yet.
    assert await _status(fit) == "screening"
    assert await _status(nofit) == "applied"
    proposals = {p["tool"]: p for p in run["proposed"]}
    assert set(proposals) == {"move_candidate", "run_payroll"}
    assert proposals["move_candidate"]["reason"] == "No Python or FastAPI"
    assert "Reject" in proposals["move_candidate"]["summary"]

    listed = (await agent.get(f"{API}/agent/actions", headers=bearer(token))).json()
    assert len(listed) == 2

    # A person approves the rejection: it happens, as them, and the candidate is told.
    done = await agent.post(f"{API}/agent/actions/{proposals['move_candidate']['id']}/approve", headers=bearer(token))
    assert done.json()["status"] == "executed", done.text
    assert await _status(nofit) == "rejected"
    async with AsyncSessionLocal() as db:
        emails = (await db.execute(select(Notification.recipient).where(Notification.event_type == "application.rejected"))).scalars().all()
    assert emails == ["nofit@acme.io"]
    again = await agent.post(f"{API}/agent/actions/{proposals['move_candidate']['id']}/approve", headers=bearer(token))
    assert again.status_code == 409

    # Payroll only runs once approved.
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(Payslip))).scalars().all() == []
    paid = await agent.post(f"{API}/agent/actions/{proposals['run_payroll']['id']}/approve", headers=bearer(token))
    assert paid.json()["result"]["result"]["processed"] == 1
    skipped = await agent.post(f"{API}/agent/actions/{proposals['run_payroll']['id']}/reject", headers=bearer(token))
    assert skipped.status_code == 409


async def test_time_off_inside_policy_is_approved_and_the_rest_waits(clients, agent, model):
    gw, hr = clients["api-gateway"], clients["hr-ops-onboarding-svc"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    emp = await _employee(gw, admin)
    soon = date.today() + timedelta(days=1)
    later = date.today() + timedelta(days=30)
    ok = (await hr.post(f"{API}/leave", json={"leave_type": "annual", "start_date": str(later),
                                              "end_date": str(later + timedelta(days=2))}, headers=bearer(emp))).json()
    short = (await hr.post(f"{API}/leave", json={"leave_type": "annual", "start_date": str(soon),
                                                 "end_date": str(soon)}, headers=bearer(emp))).json()
    model([
        [("list_time_off_requests", {})],
        [("decide_leave", {"leave_id": ok["id"], "decision": "approve"}),
         ("decide_leave", {"leave_id": short["id"], "decision": "approve", "reason": "Short notice but one day"})],
        "Approved one; one needs you.",
    ])
    run = (await agent.post(f"{API}/agent/run", json={}, headers=bearer(admin))).json()
    assert run["steps"][0]["result"]["result"][0]["days_left_before_this"] == 20
    async with AsyncSessionLocal() as db:
        statuses = {lv.id: lv.status.value for lv in (await db.execute(select(LeaveRequest))).scalars()}
    assert statuses == {ok["id"]: "approved", short["id"]: "pending"}
    assert [p["summary"] for p in run["proposed"]][0].endswith("(less than 3 business days' notice)")


async def test_employees_only_get_self_service_tools(clients, agent, model):
    gw = clients["api-gateway"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    emp = await _employee(gw, admin)
    start = date.today() + timedelta(days=20)
    m = model([
        [("list_team", {}),
         ("request_time_off", {"leave_type": "annual", "start_date": str(start), "end_date": str(start + timedelta(days=4))})],
        "Booked. HR will confirm.",
    ])
    run = (await agent.post(f"{API}/agent/chat", json={"message": "Book me a week off"}, headers=bearer(emp))).json()
    assert "list_team" not in m.offered[0] and "run_payroll" not in m.offered[0]
    assert {"request_time_off", "my_time_off", "search_policies"} <= m.offered[0]
    assert "error" in run["steps"][0]["result"]
    assert run["steps"][1]["result"]["result"]["days"] == 5
    # Staff-only endpoints stay closed.
    assert (await agent.post(f"{API}/agent/run", json={}, headers=bearer(emp))).status_code == 403
    assert (await agent.get(f"{API}/agent/actions", headers=bearer(emp))).status_code == 403


async def test_agent_cannot_reach_another_workspace(clients, agent, model):
    _, _, _, (fit, _) = await _workspace(clients)
    other = (await signup(clients["api-gateway"], "Globex", "b@globex.io"))["access_token"]
    model([[("move_candidate", {"application_id": fit, "stage": "screening"})], "Nothing to do."])
    run = (await agent.post(f"{API}/agent/run", json={}, headers=bearer(other))).json()
    assert "No application" in run["steps"][0]["result"]["error"]
    assert await _status(fit) == "applied"
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(AgentAction))).scalars().all() == []


async def test_agent_without_a_model_says_so(clients, agent, monkeypatch):
    admin = (await signup(clients["api-gateway"], "Acme", "a@acme.io"))["access_token"]
    run = await agent.post(f"{API}/agent/run", json={}, headers=bearer(admin))
    assert run.status_code == 200
    assert run.json()["status"] == "failed" and "GROQ_API_KEY" in run.json()["reply"]


async def test_unknown_arguments_are_ignored(clients, agent, model):
    gw = clients["api-gateway"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    emp = await _employee(gw, admin)
    model([[("my_time_off", {"query": "", "year": 2026})], "You have 20 days."])
    run = (await agent.post(f"{API}/agent/chat", json={"message": "days left?"}, headers=bearer(emp))).json()
    assert run["steps"][0]["result"]["result"]["days_left_this_year"]["annual"] == 20


async def test_new_application_is_read_and_screened_by_the_agent(clients, agent, model, monkeypatch, tmp_path):
    import re

    from shared.core.config import get_settings
    from shared.models.agent import AgentRun

    monkeypatch.setattr(get_settings(), "agent_screen_new_applications", True)
    gw, me, rs = clients["api-gateway"], clients["matching-engine-svc"], clients["resume-parsing-svc"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(admin))).json()
    cand = await make_candidate(gw, "acme", "dev@acme.io")
    resume = "Dana Dev\ndana@example.com +1 555 123 4567\n6 years experience building Python and FastAPI services."
    up = await rs.post(f"{API}/resumes/upload", files={"file": ("cv.txt", resume.encode(), "text/plain")},
                       headers=bearer(cand))
    assert up.status_code == 200, up.text

    def app_id(messages) -> int:
        return int(re.search(r"application (\d+)", messages[-1]["content"]).group(1))

    m = model([
        lambda msgs: [("read_resume", {"application_id": app_id(msgs)})],
        lambda msgs: [("move_candidate", {"application_id": app_id(msgs[:2]), "stage": "screening"})],
        "Moved to screening: has Python, FastAPI and 6 years.",
    ])
    applied = (await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand))).json()

    assert await _status(applied["id"]) == "screening"
    read = m.seen[1][-1]["content"]
    assert "Python" in read and "dana@example.com" not in read and "555 123" not in read
    async with AsyncSessionLocal() as db:
        runs = (await db.execute(select(AgentRun.trigger))).scalars().all()
    assert runs == ["application"]


async def test_hiring_someone_starts_onboarding_the_agent_can_track(clients, agent, model):
    _, token, _, (fit, _) = await _workspace(clients)
    me, hr = clients["matching-engine-svc"], clients["hr-ops-onboarding-svc"]
    assert (await me.patch(f"{API}/applications/{fit}/status", json={"status": "hired"},
                           headers=bearer(token))).status_code == 200
    plans = (await hr.get(f"{API}/onboarding", headers=bearer(token))).json()
    assert len(plans) == 1 and plans[0]["employee_email"] == "fit@acme.io" and plans[0]["role"] == JOB["title"]
    async with AsyncSessionLocal() as db:
        welcome = (await db.execute(select(Notification).where(Notification.event_type == "onboarding.started"))).scalar_one()
    assert welcome.recipient == "fit@acme.io" and "Submit signed offer letter" in welcome.body

    plan = plans[0]
    first = plan["tasks"][0]["id"]
    model([
        [("list_onboarding", {}), ("start_onboarding", {"name": "Fit", "email": "FIT@acme.io", "role": "x"}),
         ("complete_onboarding_task", {"onboarding_id": plan["id"], "task_id": first})],
        "Ticked one task.",
    ])
    run = (await agent.post(f"{API}/agent/run", json={}, headers=bearer(token))).json()
    assert run["steps"][0]["result"]["result"][0]["tasks"][0]["done"] is False
    assert run["steps"][1]["result"]["result"]["already_open"] is True
    assert run["steps"][2]["result"]["result"]["tasks_left"] == len(plan["tasks"]) - 1

    for t in plan["tasks"][1:]:
        r = await hr.patch(f"{API}/onboarding/{plan['id']}/tasks/{t['id']}", json={"completed": True}, headers=bearer(token))
    assert r.json()["status"] == "completed"
    assert (await hr.patch(f"{API}/onboarding/{plan['id']}/tasks/nope", json={"completed": True},
                           headers=bearer(token))).status_code == 404


async def test_handbook_upload_is_private_and_answers_policy_questions(clients, agent, model, monkeypatch):
    from shared.services import handbook

    store: list[dict] = []
    monkeypatch.setattr(handbook, "embed_batch", lambda texts: [[0.0] * 384 for _ in texts])
    monkeypatch.setattr(handbook, "_upsert", lambda points: store.extend(p.payload for p in points))
    monkeypatch.setattr(handbook, "_delete", lambda org, doc: store[:] and [
        store.remove(p) for p in list(store) if p["organization_id"] == org and p["document_id"] == doc])
    monkeypatch.setattr(handbook, "_search", lambda org, q, limit: [
        {"payload": p} for p in ([{"organization_id": 0, "title": None, "doc_id": "leave-001",
                                   "text": "Sample: 20 days of annual leave."}] + store)
        if p["organization_id"] == org][:limit])

    gw = clients["api-gateway"]
    a = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]
    text = ("Acme Leave Policy\n\nEveryone gets 25 days of paid leave a year.\n\n" + "Remote work is fine. " * 80).encode()
    up = await agent.post(f"{API}/handbook", files={"file": ("acme-leave_policy.md", text, "text/markdown")},
                          headers=bearer(a))
    assert up.status_code == 201, up.text
    doc = up.json()
    assert doc["title"] == "acme leave policy" and doc["chunks"] >= 2
    assert all(p["organization_id"] != 0 for p in store) and len(store) == doc["chunks"]
    assert (await agent.post(f"{API}/handbook", files={"file": ("x.exe", b"MZ", "application/octet-stream")},
                             headers=bearer(a))).status_code == 400

    assert (await agent.get(f"{API}/handbook", headers=bearer(b))).json() == []
    assert (await agent.delete(f"{API}/handbook/{doc['id']}", headers=bearer(b))).status_code == 404

    model([[("search_policies", {"query": "how much leave"})], "25 days."])
    own = (await agent.post(f"{API}/agent/chat", json={"message": "leave?"}, headers=bearer(a))).json()
    hits = own["steps"][0]["result"]["result"]
    assert hits[0]["from_company_handbook"] is True and "25 days" in hits[0]["text"]

    model([[("search_policies", {"query": "how much leave"})], "20 days."])
    other = (await agent.post(f"{API}/agent/chat", json={"message": "leave?"}, headers=bearer(b))).json()
    assert other["steps"][0]["result"]["result"] == [
        {"source": "leave-001", "text": "Sample: 20 days of annual leave.", "from_company_handbook": False}]

    assert (await agent.delete(f"{API}/handbook/{doc['id']}", headers=bearer(a))).status_code == 204
    assert store == [] and (await agent.get(f"{API}/handbook", headers=bearer(a))).json() == []


def test_handbook_chunks_overlap_and_cover_the_text():
    from shared.services.handbook import chunk_text

    text = "\n\n".join(f"Rule {i}. " + "Words here. " * 20 for i in range(12))
    chunks = chunk_text(text)
    assert len(chunks) > 3 and all(len(c) <= 900 for c in chunks)
    assert all(f"Rule {i}." in " ".join(chunks) for i in range(12))
    assert chunk_text("   \n\n ") == []


async def test_a_new_proposal_replaces_the_old_one_for_the_same_thing(clients, agent, model):
    _, token, _, (fit, _) = await _workspace(clients)
    model([
        [("move_candidate", {"application_id": fit, "stage": "rejected", "reason": "first idea"}),
         ("move_candidate", {"application_id": fit, "stage": "offer", "reason": "second idea"})],
        "Proposed an offer.",
    ])
    await agent.post(f"{API}/agent/run", json={}, headers=bearer(token))
    waiting = (await agent.get(f"{API}/agent/actions", headers=bearer(token))).json()
    assert [(a["reason"], a["summary"].split()[0]) for a in waiting] == [("second idea", "Make")]


async def test_payroll_is_not_proposed_when_everyone_is_paid(clients, agent, model):
    admin = await signup(clients["api-gateway"], "Acme", "a@acme.io")
    token, pay = admin["access_token"], clients["payroll-automation-svc"]
    await pay.put(f"{API}/payroll/profile", json={"user_id": admin["user"]["id"], "annual_base": 120000}, headers=bearer(token))
    last = date.today().replace(day=1) - timedelta(days=1)
    await pay.post(f"{API}/payroll/run-all", json={"period_start": str(last.replace(day=1)), "period_end": str(last)},
                   headers=bearer(token))
    model([[("run_payroll", {"month": last.strftime("%Y-%m")})], "Already paid."])
    run = (await agent.post(f"{API}/agent/run", json={}, headers=bearer(token))).json()
    assert "already paid" in run["steps"][0]["result"]["error"] and run["proposed"] == []


async def test_admins_are_emailed_when_the_agent_needs_their_ok(clients, agent, model, monkeypatch):
    from shared.core.config import get_settings

    monkeypatch.setattr(get_settings(), "agent_screen_new_applications", True)
    gw, me = clients["api-gateway"], clients["matching-engine-svc"]
    founder = (await signup(gw, "Acme", "founder@acme.io"))["access_token"]
    invite = (await gw.post(f"{API}/users/invite", json={"email": "cofounder@acme.io", "role": "admin"},
                            headers=bearer(founder))).json()
    cofounder = (await gw.post(f"{API}/auth/accept-invite", json={
        "token": invite["invite_url"].split("token=")[1], "full_name": "Co Founder", "password": "cofounder-pass-1",
    })).json()["access_token"]
    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(founder))).json()
    cand = await make_candidate(gw, "acme", "nope@acme.io")

    async def approval_emails():
        async with AsyncSessionLocal() as db:
            return sorted((n.recipient, n.subject, n.body) for n in (await db.execute(
                select(Notification).where(Notification.event_type == "agent.approval_needed"))).scalars())

    # Nobody started this run (a new application did), so every admin hears about it.
    def app_id(messages) -> int:
        import re
        return int(re.search(r"application (\d+)", messages[-1]["content"]).group(1))
    model([lambda msgs: [("move_candidate", {"application_id": app_id(msgs), "stage": "rejected",
                                             "reason": "No Python or FastAPI"})], "Proposed a rejection."])
    await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand))
    sent = await approval_emails()
    assert [r for r, _, _ in sent] == ["cofounder@acme.io", "founder@acme.io"]
    subject, body = sent[0][1], sent[0][2]
    assert subject == "Your OK needed: Reject Cand (Backend Engineer)"
    assert "Why: No Python or FastAPI" in body and "/admin#approvals" in body

    # The founder runs it themselves: they see it on screen, only the co-founder is emailed.
    monkeypatch.setattr(get_settings(), "agent_screen_new_applications", False)
    model([[("move_candidate", {"application_id": 1, "stage": "offer", "reason": "x"})], "Proposed."])
    await agent.post(f"{API}/agent/run", json={}, headers=bearer(founder))
    assert [r for r, _, _ in await approval_emails()] == ["cofounder@acme.io", "cofounder@acme.io", "founder@acme.io"]

    # Nothing waiting, no email.
    model(["All quiet."])
    await agent.post(f"{API}/agent/run", json={}, headers=bearer(cofounder))
    assert len(await approval_emails()) == 3
