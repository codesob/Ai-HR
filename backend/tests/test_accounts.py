import re

import pytest

from tests.conftest import bearer, signup

API = "/api/v1"


@pytest.fixture
def outbox(monkeypatch):
    """Captures account emails instead of sending them; each item is (to, subject, link)."""
    import shared.api.auth as auth

    sent: list[tuple[str, str, str]] = []

    async def capture(to: str, subject: str, body: str, link: str) -> None:
        sent.append((to, subject, link))

    monkeypatch.setattr(auth, "send_account_email", capture)
    return sent


def token_from(link: str) -> str:
    return re.search(r"token=([\w-]+)", link).group(1)


async def test_browser_session_uses_httponly_cookies_and_refresh_rotates(clients):
    gw = clients["api-gateway"]
    await signup(gw, "Cookie Co", "owner@cookie.io")
    assert gw.cookies.get("aihr_access") and gw.cookies.get("aihr_refresh")

    raw_set_cookie = " ".join(v for k, v in (await gw.post(f"{API}/auth/refresh")).headers.multi_items() if k == "set-cookie")
    assert "HttpOnly" in raw_set_cookie and "SameSite=lax" in raw_set_cookie
    assert f"Path={API}/auth" in raw_set_cookie  # refresh cookie never sent to ordinary endpoints

    # No Authorization header: the cookie alone authenticates, at the gateway and at downstream services.
    assert (await gw.get(f"{API}/auth/me")).json()["email"] == "owner@cookie.io"
    jobs = await clients["matching-engine-svc"].get(f"{API}/jobs", headers={"Cookie": f"aihr_access={gw.cookies['aihr_access']}"})
    assert jobs.status_code == 200

    old_refresh = gw.cookies["aihr_refresh"]
    assert (await gw.post(f"{API}/auth/refresh")).status_code == 200
    assert gw.cookies["aihr_refresh"] != old_refresh
    gw.cookies.set("aihr_refresh", old_refresh, path=f"{API}/auth")
    replay = await gw.post(f"{API}/auth/refresh")
    assert replay.status_code == 401  # a used refresh token can't be replayed


async def test_cookie_writes_from_other_sites_are_blocked(clients):
    gw = clients["api-gateway"]
    await signup(gw, "Csrf Co", "owner@csrf.io")
    rename = {"full_name": "Hijacked"}

    evil = await gw.patch(f"{API}/account/profile", json=rename, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    gw.headers.pop("Origin")
    no_origin = await gw.patch(f"{API}/account/profile", json=rename)
    assert no_origin.status_code == 403
    assert (await gw.get(f"{API}/auth/me")).json()["full_name"] == "Owner"
    ok = await gw.patch(f"{API}/account/profile", json={"full_name": "Dana"}, headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 200, ok.text


async def test_logout_ends_the_session_immediately(clients):
    gw = clients["api-gateway"]
    token = (await signup(gw, "Logout Co", "owner@logout.io"))["access_token"]
    assert (await gw.get(f"{API}/auth/me", headers=bearer(token))).status_code == 200

    assert (await gw.post(f"{API}/auth/logout")).status_code == 204
    assert "aihr_access" not in gw.cookies
    # The access token is still unexpired, but its session is revoked.
    after = await gw.get(f"{API}/auth/me", headers=bearer(token))
    assert after.status_code == 401


async def test_password_reset_flow(clients, outbox):
    gw = clients["api-gateway"]
    await signup(gw, "Reset Co", "owner@reset.io")
    old_session = (await gw.post(f"{API}/auth/login", json={"email": "owner@reset.io", "password": "correct-horse-1"})).json()

    unknown = await gw.post(f"{API}/auth/password/forgot", json={"email": "nobody@reset.io"})
    known = await gw.post(f"{API}/auth/password/forgot", json={"email": "owner@reset.io"})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()  # doesn't reveal which emails have accounts
    resets = [link for to, subject, link in outbox if "Reset" in subject]
    assert len(resets) == 1 and "/reset-password?token=" in resets[0]

    token = token_from(resets[0])
    short = await gw.post(f"{API}/auth/password/reset", json={"token": token, "password": "short"})
    assert short.status_code == 422
    r = await gw.post(f"{API}/auth/password/reset", json={"token": token, "password": "brand-new-pass-2"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email_verified_at"]

    assert (await gw.post(f"{API}/auth/password/reset", json={"token": token, "password": "another-pass-3"})).status_code == 400
    assert (await gw.get(f"{API}/auth/me", headers=bearer(old_session["access_token"]))).status_code == 401
    assert (await gw.post(f"{API}/auth/login", json={"email": "owner@reset.io", "password": "correct-horse-1"})).status_code == 401
    assert (await gw.post(f"{API}/auth/login", json={"email": "owner@reset.io", "password": "brand-new-pass-2"})).status_code == 200


async def test_new_reset_link_replaces_the_previous_one(clients, outbox):
    gw = clients["api-gateway"]
    await signup(gw, "Twice Co", "owner@twice.io")
    await gw.post(f"{API}/auth/password/forgot", json={"email": "owner@twice.io"})
    await gw.post(f"{API}/auth/password/forgot", json={"email": "owner@twice.io"})
    first, second = [token_from(link) for _, subject, link in outbox if "Reset" in subject]
    assert (await gw.post(f"{API}/auth/password/reset", json={"token": first, "password": "brand-new-pass-2"})).status_code == 400
    assert (await gw.post(f"{API}/auth/password/reset", json={"token": second, "password": "brand-new-pass-2"})).status_code == 200


async def test_signup_sends_verification_and_link_confirms_email(clients, outbox):
    gw = clients["api-gateway"]
    data = await signup(gw, "Verify Co", "owner@verify.io")
    assert data["user"]["email_verified_at"] is None
    verify = [link for to, subject, link in outbox if to == "owner@verify.io" and "Confirm" in subject]
    assert len(verify) == 1

    r = await gw.post(f"{API}/auth/email/verify", json={"token": token_from(verify[0])})
    assert r.status_code == 200 and r.json()["email_verified_at"]
    assert (await gw.get(f"{API}/auth/me")).json()["email_verified_at"]
    assert (await gw.post(f"{API}/auth/email/verify", json={"token": token_from(verify[0])})).status_code == 400


async def test_change_password_and_manage_sessions(clients):
    gw = clients["api-gateway"]
    await signup(gw, "Devices Co", "owner@devices.io")
    laptop = (await gw.post(f"{API}/auth/login", json={"email": "owner@devices.io", "password": "correct-horse-1"})).json()
    phone = (await gw.post(f"{API}/auth/login", json={"email": "owner@devices.io", "password": "correct-horse-1"})).json()

    sessions = (await gw.get(f"{API}/account/sessions", headers=bearer(laptop["access_token"]))).json()
    assert len(sessions) == 3 and sum(s["current"] for s in sessions) == 1

    wrong = await gw.post(f"{API}/account/password", headers=bearer(laptop["access_token"]),
                          json={"current_password": "nope", "new_password": "changed-pass-22"})
    assert wrong.status_code == 400
    ok = await gw.post(f"{API}/account/password", headers=bearer(laptop["access_token"]),
                       json={"current_password": "correct-horse-1", "new_password": "changed-pass-22"})
    assert ok.status_code == 204
    # Changing the password keeps this device signed in and signs every other device out.
    assert (await gw.get(f"{API}/auth/me", headers=bearer(laptop["access_token"]))).status_code == 200
    assert (await gw.get(f"{API}/auth/me", headers=bearer(phone["access_token"]))).status_code == 401

    profile = await gw.patch(f"{API}/account/profile", headers=bearer(laptop["access_token"]), json={"full_name": "Dana Owner"})
    assert profile.json()["full_name"] == "Dana Owner"


async def test_users_cannot_end_other_users_sessions(clients):
    gw = clients["api-gateway"]
    a = await signup(gw, "Alpha", "a@alpha.io")
    b = await signup(gw, "Beta", "b@beta.io")
    b_sessions = (await gw.get(f"{API}/account/sessions", headers=bearer(b["access_token"]))).json()
    await gw.delete(f"{API}/account/sessions/{b_sessions[0]['id']}", headers=bearer(a["access_token"]))
    assert (await gw.get(f"{API}/auth/me", headers=bearer(b["access_token"]))).status_code == 200


async def test_shared_demo_accounts_cannot_be_locked(clients, outbox):
    from shared.db.seed import seed_demo_data

    await seed_demo_data()
    gw = clients["api-gateway"]
    demo = (await gw.post(f"{API}/auth/login", json={"email": "admin@aihr.demo", "password": "demo12345"})).json()
    h = bearer(demo["access_token"])
    attempts = [
        await gw.post(f"{API}/account/password", headers=h, json={"current_password": "demo12345", "new_password": "hijacked-pass-1"}),
        await gw.patch(f"{API}/account/profile", headers=h, json={"full_name": "Hijacked"}),
        await gw.post(f"{API}/account/sessions/revoke-others", headers=h),
    ]
    assert [r.status_code for r in attempts] == [403, 403, 403]
    await gw.post(f"{API}/auth/password/forgot", json={"email": "admin@aihr.demo"})
    assert not [m for m in outbox if m[0] == "admin@aihr.demo"]
    assert (await gw.post(f"{API}/auth/login", json={"email": "admin@aihr.demo", "password": "demo12345"})).status_code == 200
