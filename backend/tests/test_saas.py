from datetime import date

import pytest
from pydantic import ValidationError

from tests.conftest import bearer, signup

API = "/api/v1"
JOB = {
    "title": "Backend Engineer",
    "description": "Build reliable Python APIs with FastAPI and PostgreSQL.",
    "required_skills": ["Python", "FastAPI"],
    "min_experience_years": 2,
}


async def make_candidate(gw, org_slug: str, email: str) -> str:
    r = await gw.post(f"{API}/auth/register", json={
        "org_slug": org_slug, "full_name": "Cand", "email": email, "password": "candidate-pass-1",
        "role": "admin",  # must be ignored
    })
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "candidate"
    return r.json()["access_token"]


async def test_signup_creates_org_admin_and_login_works(clients):
    gw = clients["api-gateway"]
    data = await signup(gw, "Acme Inc", "owner@acme.io")
    assert data["user"]["role"] == "admin"

    me = await gw.get(f"{API}/auth/me", headers=bearer(data["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == "owner@acme.io"
    org = await gw.get(f"{API}/auth/organization", headers=bearer(data["access_token"]))
    assert org.json()["slug"] == "acme-inc"

    bad = await gw.post(f"{API}/auth/login", json={"email": "owner@acme.io", "password": "wrong-password"})
    assert bad.status_code == 401
    ok = await gw.post(f"{API}/auth/login", json={"email": "OWNER@acme.io", "password": "correct-horse-1"})
    assert ok.status_code == 200

    dup = await gw.post(f"{API}/auth/signup", json={
        "company_name": "Other", "full_name": "X", "email": "owner@acme.io", "password": "correct-horse-1",
    })
    assert dup.status_code == 409


async def test_signup_and_login_with_password_over_72_bytes(clients):
    gw = clients["api-gateway"]
    password = "é" * 50 + "long-pass"  # 109 UTF-8 bytes, beyond bcrypt's 72-byte limit
    r = await gw.post(f"{API}/auth/signup", json={
        "company_name": "Longpass", "full_name": "Owner", "email": "lp@acme.io", "password": password,
    })
    assert r.status_code == 201, r.text
    ok = await gw.post(f"{API}/auth/login", json={"email": "lp@acme.io", "password": password})
    assert ok.status_code == 200, ok.text


async def test_store_file_rejects_unsafe_keys():
    from shared.services.storage import store_file

    for key in ("../escape.txt", "org-1/../../escape.txt", "/abs.txt", "org-1//x.txt", ""):
        with pytest.raises(ValueError):
            await store_file(b"x", key)
    assert (await store_file(b"x", "org-1/resumes/1_abc.txt")).endswith("1_abc.txt")


async def test_reranker_fallback_keeps_order_without_scores_or_mutation():
    from shared.services.nvidia_reranker import NvidiaReranker

    docs = [{"text": "a", "id": 1}, {"text": "b", "id": 2}]
    out = await NvidiaReranker().rerank("q", docs, top_k=1)
    assert out == [{"text": "a", "id": 1, "score": None, "rank": 1, "reranked": False}]
    assert docs == [{"text": "a", "id": 1}, {"text": "b", "id": 2}]
    assert await NvidiaReranker().rerank("q", []) == []


async def test_tampered_or_missing_token_rejected(clients):
    gw, me = clients["api-gateway"], clients["matching-engine-svc"]
    token = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    assert (await me.get(f"{API}/jobs")).status_code == 401
    assert (await me.get(f"{API}/jobs", headers=bearer(token[:-2] + "xx"))).status_code == 401


async def test_tenant_isolation_for_jobs_and_applications(clients):
    gw, me = clients["api-gateway"], clients["matching-engine-svc"]
    a = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]

    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(a))).json()

    assert (await me.get(f"{API}/jobs", headers=bearer(b))).json() == []
    assert (await me.get(f"{API}/jobs/{job['id']}", headers=bearer(b))).status_code == 404
    assert (await me.patch(f"{API}/jobs/{job['id']}", json={"status": "closed"}, headers=bearer(b))).status_code == 404
    assert (await me.get(f"{API}/applications/ranked/{job['id']}", headers=bearer(b))).status_code == 404

    public = await me.get(f"{API}/jobs/public/acme")
    assert [j["id"] for j in public.json()] == [job["id"]]
    assert (await me.get(f"{API}/jobs/public/globex")).json() == []

    cand_b = await make_candidate(gw, "globex", "c@globex.io")
    assert (await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand_b))).status_code == 404

    cand_a = await make_candidate(gw, "acme", "c@acme.io")
    applied = await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand_a))
    assert applied.status_code == 201, applied.text
    assert 0 <= applied.json()["match_score"] <= 1
    assert (await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand_a))).status_code == 409

    assert len((await me.get(f"{API}/applications", headers=bearer(a))).json()) == 1
    assert (await me.get(f"{API}/applications", headers=bearer(b))).json() == []
    assert len((await me.get(f"{API}/applications/mine", headers=bearer(cand_a))).json()) == 1


async def test_candidates_cannot_use_staff_endpoints(clients):
    gw, me, an = clients["api-gateway"], clients["matching-engine-svc"], clients["analytics-dashboard-svc"]
    await signup(gw, "Acme", "a@acme.io")
    cand = await make_candidate(gw, "acme", "c@acme.io")
    assert (await me.post(f"{API}/jobs", json=JOB, headers=bearer(cand))).status_code == 403
    assert (await me.get(f"{API}/applications", headers=bearer(cand))).status_code == 403
    assert (await an.get(f"{API}/analytics/hiring", headers=bearer(cand))).status_code == 403
    assert (await gw.post(f"{API}/users/invite", json={"email": "x@acme.io", "role": "admin"},
                          headers=bearer(cand))).status_code == 403


async def test_invite_flow_assigns_invited_role(clients):
    gw = clients["api-gateway"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    invite = await gw.post(f"{API}/users/invite", json={"email": "rec@acme.io", "role": "recruiter"},
                           headers=bearer(admin))
    assert invite.status_code == 201, invite.text
    token = invite.json()["invite_url"].split("token=")[1]

    accepted = await gw.post(f"{API}/auth/accept-invite",
                             json={"token": token, "full_name": "Rec", "password": "recruiter-pass-1"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["user"]["role"] == "recruiter"
    again = await gw.post(f"{API}/auth/accept-invite",
                          json={"token": token, "full_name": "Rec", "password": "recruiter-pass-1"})
    assert again.status_code == 400

    users = (await gw.get(f"{API}/users", headers=bearer(admin))).json()
    assert {u["email"] for u in users} == {"a@acme.io", "rec@acme.io"}


async def test_admin_cannot_lock_themselves_out(clients):
    gw = clients["api-gateway"]
    data = await signup(gw, "Acme", "a@acme.io")
    r = await gw.patch(f"{API}/users/{data['user']['id']}", json={"role": "employee"},
                       headers=bearer(data["access_token"]))
    assert r.status_code == 400


async def test_hiring_analytics_are_scoped_and_track_time_to_hire(clients):
    gw, me, an = clients["api-gateway"], clients["matching-engine-svc"], clients["analytics-dashboard-svc"]
    a = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]
    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(a))).json()
    cand = await make_candidate(gw, "acme", "c@acme.io")
    app_id = (await me.post(f"{API}/applications/apply/{job['id']}", headers=bearer(cand))).json()["id"]
    r = await me.patch(f"{API}/applications/{app_id}/status", json={"status": "hired"}, headers=bearer(a))
    assert r.status_code == 200 and r.json()["status"] == "hired"

    stats_a = (await an.get(f"{API}/analytics/hiring", headers=bearer(a))).json()
    assert stats_a["total_applications"] == 1 and stats_a["funnel"]["hired"] == 1
    assert stats_a["avg_time_to_hire_days"] == 0
    assert stats_a["source_effectiveness"] == {"careers_page": 100}
    stats_b = (await an.get(f"{API}/analytics/hiring", headers=bearer(b))).json()
    assert stats_b["total_applications"] == 0 and stats_b["total_jobs"] == 0


async def test_payroll_scoped_to_organization(clients):
    gw, pay = clients["api-gateway"], clients["payroll-automation-svc"]
    a = await signup(gw, "Acme", "a@acme.io")
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]
    user_a = a["user"]["id"]

    assert (await pay.put(f"{API}/payroll/profile", json={"user_id": user_a, "annual_base": 120000},
                          headers=bearer(b))).status_code == 404
    assert (await pay.put(f"{API}/payroll/profile", json={"user_id": user_a, "annual_base": 120000},
                          headers=bearer(a["access_token"]))).status_code == 200
    run = {"user_id": user_a, "period_start": "2026-10-01", "period_end": "2026-10-31"}
    assert (await pay.post(f"{API}/payroll/run", json=run, headers=bearer(b))).status_code == 404
    slip = await pay.post(f"{API}/payroll/run", json=run, headers=bearer(a["access_token"]))
    assert slip.status_code == 201 and slip.json()["gross_amount"] == 10000
    assert (await pay.post(f"{API}/payroll/run", json=run, headers=bearer(a["access_token"]))).status_code == 409


async def test_org_payroll_run_pays_everyone_once_and_stays_scoped(clients):
    gw, pay = clients["api-gateway"], clients["payroll-automation-svc"]
    a = await signup(gw, "Acme", "a@acme.io")
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]
    admin_a = bearer(a["access_token"])
    await pay.put(f"{API}/payroll/profile", json={"user_id": a["user"]["id"], "annual_base": 120000}, headers=admin_a)

    rows = (await pay.get(f"{API}/payroll/profiles", headers=admin_a)).json()
    assert [(r["full_name"], r["annual_base"], r["last_net_amount"]) for r in rows] == [("Owner", 120000, None)]
    assert (await pay.get(f"{API}/payroll/profiles", headers=bearer(b))).json()[0]["annual_base"] is None

    period = {"period_start": "2026-10-01", "period_end": "2026-10-31"}
    first = (await pay.post(f"{API}/payroll/run-all", json=period, headers=admin_a)).json()
    assert first["processed"] == 1 and first["skipped"] == 0 and first["total_net"] > 0
    again = (await pay.post(f"{API}/payroll/run-all", json=period, headers=admin_a)).json()
    assert again == {"processed": 0, "skipped": 1, "total_net": 0, "bs_month": "Kartik 2083", "fiscal_year": "2083/84"}
    assert (await pay.post(f"{API}/payroll/run-all", json=period, headers=bearer(b))).json()["processed"] == 0
    assert (await pay.get(f"{API}/payroll/profiles", headers=admin_a)).json()[0]["last_period_end"] == "2026-10-31"


async def test_changes_are_recorded_in_workspace_audit_log(clients):
    gw = clients["api-gateway"]
    a = await signup(gw, "Acme", "a@acme.io")
    b = (await signup(gw, "Globex", "b@globex.io"))["access_token"]
    admin_a = bearer(a["access_token"])
    from shared.services.audit import flush_pending_audit_events

    invite = await gw.post(f"{API}/users/invite", json={"email": "r@acme.io", "role": "recruiter"}, headers=admin_a)
    assert invite.status_code == 201
    await flush_pending_audit_events()

    log = (await gw.get(f"{API}/users/audit", headers=admin_a)).json()
    assert log[0]["actor"] == "a@acme.io" and log[0]["action"] == "POST"
    assert log[0]["resource"] == f"{API}/users/invite" and log[0]["status_code"] == 201
    assert (await gw.get(f"{API}/users/audit", headers=bearer(b))).json() == []

    recruiter = (await gw.post(f"{API}/auth/accept-invite", json={
        "token": invite.json()["invite_url"].split("token=")[1], "full_name": "Rec", "password": "recruiter-pass-1",
    })).json()["access_token"]
    assert (await gw.get(f"{API}/users/audit", headers=bearer(recruiter))).status_code == 403


async def test_leave_request_and_review(clients):
    gw, hr = clients["api-gateway"], clients["hr-ops-onboarding-svc"]
    admin = (await signup(gw, "Acme", "a@acme.io"))["access_token"]
    invite = (await gw.post(f"{API}/users/invite", json={"email": "e@acme.io", "role": "employee"},
                            headers=bearer(admin))).json()
    emp = (await gw.post(f"{API}/auth/accept-invite", json={
        "token": invite["invite_url"].split("token=")[1], "full_name": "Emp", "password": "employee-pass-1",
    })).json()["access_token"]

    bad = await hr.post(f"{API}/leave", json={"leave_type": "annual", "start_date": "2026-11-05",
                                              "end_date": "2026-11-01"}, headers=bearer(emp))
    assert bad.status_code == 422
    leave = await hr.post(f"{API}/leave", json={"leave_type": "annual", "start_date": "2026-11-01",
                                                "end_date": "2026-11-05", "reason": "Trip"}, headers=bearer(emp))
    assert leave.status_code == 201
    assert (await hr.post(f"{API}/leave/{leave.json()['id']}/review", json={"status": "approved"},
                          headers=bearer(emp))).status_code == 403
    reviewed = await hr.post(f"{API}/leave/{leave.json()['id']}/review", json={"status": "approved"},
                             headers=bearer(admin))
    assert reviewed.json()["status"] == "approved"


async def test_resume_upload_size_limit_and_parse(clients, monkeypatch):
    gw, rs = clients["api-gateway"], clients["resume-parsing-svc"]
    await signup(gw, "Acme", "a@acme.io")
    cand = await make_candidate(gw, "acme", "c@acme.io")
    text = b"Jane Doe\njane@example.com\nSkills: Python, FastAPI, Docker\n5 years experience"
    ok = await rs.post(f"{API}/resumes/upload", files={"file": ("cv.txt", text, "text/plain")}, headers=bearer(cand))
    assert ok.status_code == 200, ok.text
    assert "Python" in ok.json()["skills"]

    big = b"x" * (6 * 1024 * 1024)
    r = await rs.post(f"{API}/resumes/upload", files={"file": ("cv.txt", big, "text/plain")}, headers=bearer(cand))
    assert r.status_code == 413
    r = await rs.post(f"{API}/resumes/upload", files={"file": ("cv.exe", b"MZ", "application/octet-stream")},
                      headers=bearer(cand))
    assert r.status_code == 400


async def test_gateway_returns_429_not_500_when_rate_limited(clients, monkeypatch):
    from shared.core.config import get_settings

    gw = clients["api-gateway"]
    import shared.api.rate_limit as rl

    rl._memory_buckets.clear()
    monkeypatch.setattr(get_settings(), "auth_rate_limit_requests", 2)
    codes = [
        (await gw.post(f"{API}/auth/login", json={"email": "x@y.io", "password": "nope"})).status_code
        for _ in range(4)
    ]
    assert codes[:2] == [401, 401] and codes[2:] == [429, 429]


async def test_gateway_reports_unavailable_upstream(clients):
    r = await clients["api-gateway"].get(f"{API}/jobs/public/acme")
    assert r.status_code in (503, 504)
    assert (await clients["api-gateway"].get(f"{API}/nope")).status_code == 404


def test_production_rejects_insecure_config(monkeypatch):
    from shared.core.config import Settings

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(environment="production", secret_key="change-me-in-production",
                 database_url="postgresql+asyncpg://u:p@db/x")
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(environment="production", secret_key="x" * 40, database_url="sqlite+aiosqlite:///x.db")
    prod = Settings(environment="production", secret_key="x" * 40, database_url="postgresql+asyncpg://u:p@db/x")
    assert prod.auto_create_schema is False and prod.seed_demo_data is False and prod.cors_origin_regex is None


def test_payroll_period_validation():
    from shared.schemas.payroll import PayrollRun

    with pytest.raises(ValidationError):
        PayrollRun(user_id=1, period_start=date(2026, 2, 1), period_end=date(2026, 1, 1))


async def test_concurrent_startup_seeding_is_safe():
    import asyncio

    from sqlalchemy import func, select

    from shared.db.seed import CANDIDATES, STAFF, seed_demo_data
    from shared.db.session import AsyncSessionLocal
    from shared.models.entities import Organization, User

    await asyncio.gather(*(seed_demo_data() for _ in range(4)))
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.count()).select_from(Organization))).scalar() == 1
        # Staff, the demo candidate login, and the showcase applicants.
        assert (await db.execute(select(func.count()).select_from(User))).scalar() == len(STAFF) + 1 + len(CANDIDATES)


async def test_demo_workspace_is_scored_by_matching_engine_and_feeds_analytics(clients):
    from shared.db.seed import APPLICATIONS, seed_demo_data
    from tests.conftest import _apps

    gw, me, an = clients["api-gateway"], clients["matching-engine-svc"], clients["analytics-dashboard-svc"]
    await seed_demo_data()
    await seed_demo_data()  # re-running must not duplicate the showcase

    matching_app = _apps["matching-engine-svc"]
    async with matching_app.router.lifespan_context(matching_app):
        pass

    login = await gw.post(f"{API}/auth/login", json={"email": "admin@aihr.demo", "password": "demo12345"})
    assert login.status_code == 200, login.text
    admin = bearer(login.json()["access_token"])

    apps = (await me.get(f"{API}/applications", headers=admin)).json()
    assert len(apps) == len(APPLICATIONS)
    assert all(a["match_score"] is not None and a["match_explanation"] for a in apps)

    ml_job = next(j for j in (await me.get(f"{API}/jobs", headers=admin)).json() if j["title"] == "Senior ML Engineer")
    ranked = (await me.get(f"{API}/applications/ranked/{ml_job['id']}", headers=admin)).json()
    assert ranked[0]["candidate_name"] == "Priya Natarajan"
    assert ranked[0]["match_explanation"]["missing_skills"] == []

    stats = (await an.get(f"{API}/analytics/hiring", headers=admin)).json()
    assert stats["funnel"]["hired"] == 2 and stats["avg_match_score"] is not None
    assert stats["avg_time_to_hire_days"] == pytest.approx((19 + 24) / 2, abs=1)
