"""Tasks, video screens, applicant emails, LinkedIn source tagging and interview video links."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from shared.db.session import AsyncSessionLocal
from shared.models.entities import Application, Notification
from shared.services import screening_ai
from tests.conftest import bearer, signup
from tests.test_saas import JOB, make_candidate

API = "/api/v1"


async def _emails(event: str | None = None) -> list[tuple[str, str]]:
    async with AsyncSessionLocal() as db:
        q = select(Notification).where(Notification.channel == "email").order_by(Notification.id)
        if event:
            q = q.where(Notification.event_type == event)
        return [(n.recipient, n.subject) for n in (await db.execute(q)).scalars()]


@pytest.fixture
async def hiring(clients):
    gw, me = clients["api-gateway"], clients["matching-engine-svc"]
    admin = (await signup(gw, "Acme", "boss@acme.io"))["access_token"]
    job = (await me.post(f"{API}/jobs", json=JOB, headers=bearer(admin))).json()
    cand = await make_candidate(gw, "acme", "ana@acme.io")
    applied = await me.post(f"{API}/applications/apply/{job['id']}?source=linkedin", headers=bearer(cand))
    return {"admin": admin, "cand": cand, "job": job, "app": applied.json()["id"],
            "iv": clients["interview-assistant-svc"], "me": me, "gw": gw}


@pytest.fixture
def ai(monkeypatch):
    async def review(*_args, **_kw):
        return screening_ai.Review(score=82, recommendation="pass", feedback="Clear, correct and well tested.")

    async def transcribe(data, filename, content_type, language=None):
        return f"Spoken answer from {filename}"

    monkeypatch.setattr(screening_ai, "review_assessment", review)
    monkeypatch.setattr(screening_ai, "review_video_answers", review)
    monkeypatch.setattr(screening_ai, "transcribe", transcribe)


async def test_applying_emails_the_applicant_and_team_and_keeps_the_linkedin_source(hiring):
    sent = await _emails()
    assert ("ana@acme.io", f"We got your application for {JOB['title']}") in sent
    assert ("boss@acme.io", f"New application via LinkedIn: Cand for {JOB['title']}") in sent
    ranked = (await hiring["me"].get(f"{API}/applications/ranked/{hiring['job']['id']}",
                                     headers=bearer(hiring["admin"]))).json()
    assert ranked[0]["source"] == "linkedin"


async def test_every_stage_change_tells_the_applicant_once(hiring):
    me, admin, app = hiring["me"], hiring["admin"], hiring["app"]
    for stage in ("screening", "offer", "rejected", "rejected"):
        await me.patch(f"{API}/applications/{app}/status", json={"status": stage}, headers=bearer(admin))
    subjects = [s for r, s in await _emails() if r == "ana@acme.io"]
    assert subjects[1:] == [f"Your application for {JOB['title']} is being reviewed",
                            f"Good news about {JOB['title']}", f"Your application for {JOB['title']}"]


async def test_task_is_reviewed_by_ai_and_decided_by_a_person(hiring, ai):
    iv, admin, cand, app = hiring["iv"], hiring["admin"], hiring["cand"], hiring["app"]
    sent = await iv.post(f"{API}/screening/applications/{app}/assessment", headers=bearer(admin), json={
        "title": "Build a tiny API", "instructions": "Write a FastAPI endpoint that returns the sum of two numbers.",
        "due_days": 3})
    assert sent.status_code == 201, sent.text
    task = sent.json()
    async with AsyncSessionLocal() as db:
        assert (await db.get(Application, app)).status.value == "assessment"
    assert ("ana@acme.io", f"Your next step for {JOB['title']}: Build a tiny API") in await _emails()

    mine = (await iv.get(f"{API}/screening/mine", headers=bearer(cand))).json()
    assert mine["assessments"][0]["title"] == "Build a tiny API" and "ai_score" not in mine["assessments"][0]
    # Nobody decides before it's handed in, and only the applicant can hand it in.
    assert (await iv.post(f"{API}/screening/assessments/{task['id']}/decision", json={"passed": True},
                          headers=bearer(admin))).status_code == 409
    assert (await iv.post(f"{API}/screening/assessments/{task['id']}/submit", json={"text": "x"},
                          headers=bearer(admin))).status_code == 403
    answer = "@app.get('/sum')\ndef total(a: int, b: int):\n    return a + b"
    done = await iv.post(f"{API}/screening/assessments/{task['id']}/submit", json={"text": answer}, headers=bearer(cand))
    assert done.status_code == 204
    assert (await iv.post(f"{API}/screening/assessments/{task['id']}/submit", json={"text": "again"},
                          headers=bearer(cand))).status_code == 409

    reviewed = (await iv.get(f"{API}/screening/applications/{app}", headers=bearer(admin))).json()["assessments"][0]
    assert (reviewed["status"], reviewed["ai_score"], reviewed["ai_recommendation"]) == ("submitted", 82, "pass")
    assert await _emails("assessment.submitted") == [("boss@acme.io", f"Cand submitted their task for {JOB['title']}")]

    decided = await iv.post(f"{API}/screening/assessments/{task['id']}/decision", json={"passed": True},
                            headers=bearer(admin))
    assert decided.json()["status"] == "passed"
    assert ("ana@acme.io", f"Next step for {JOB['title']}") in await _emails()


async def test_video_screen_records_transcribes_reviews_and_failing_rejects(hiring, ai):
    iv, admin, cand, app = hiring["iv"], hiring["admin"], hiring["cand"], hiring["app"]
    screen = (await iv.post(f"{API}/screening/applications/{app}/video", json={}, headers=bearer(admin))).json()
    assert len(screen["questions"]) == 3 and JOB["title"] in screen["questions"][0]

    video = b"\x1aE\xdf\xa3fake-webm"
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/complete", headers=bearer(cand))).status_code == 409
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/answers/0", headers=bearer(cand),
                          files={"file": ("a.txt", b"hi", "text/plain")})).status_code == 409
    for i in range(3):
        r = await iv.post(f"{API}/screening/video/{screen['id']}/answers/{i}", headers=bearer(cand),
                          files={"file": (f"a{i}.webm", video, "video/webm;codecs=vp8,opus")})
        assert r.status_code == 204, r.text
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/answers/9", headers=bearer(cand),
                          files={"file": ("x.webm", video, "video/webm")})).status_code == 409
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/complete", headers=bearer(cand))).status_code == 204

    got = (await iv.get(f"{API}/screening/applications/{app}", headers=bearer(admin))).json()["video_screens"][0]
    assert got["status"] == "completed" and got["ai_recommendation"] == "pass"
    assert got["answers"][1]["transcript"] == "Spoken answer from answer-1.webm"
    played = await iv.get(f"{API}/screening/video/{screen['id']}/answers/1", headers=bearer(admin))
    assert played.status_code == 200 and played.content == video and played.headers["content-type"] == "video/webm"

    failed = await iv.post(f"{API}/screening/video/{screen['id']}/decision", json={"passed": False},
                           headers=bearer(admin))
    assert failed.json()["status"] == "failed"
    async with AsyncSessionLocal() as db:
        assert (await db.get(Application, app)).status.value == "rejected"
    assert ("ana@acme.io", f"Your application for {JOB['title']}") in await _emails()


async def test_other_companies_cannot_see_or_decide(hiring):
    other = (await signup(hiring["gw"], "Globex", "g@globex.io"))["access_token"]
    iv, app = hiring["iv"], hiring["app"]
    assert (await iv.post(f"{API}/screening/applications/{app}/video", json={}, headers=bearer(other))).status_code == 404
    screen = (await iv.post(f"{API}/screening/applications/{app}/video", json={}, headers=bearer(hiring["admin"]))).json()
    assert (await iv.get(f"{API}/screening/applications/{app}", headers=bearer(other))).json() == {
        "assessments": [], "video_screens": []}
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/decision", json={"passed": True},
                          headers=bearer(other))).status_code == 404
    stranger = await make_candidate(hiring["gw"], "acme", "eve@acme.io")
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/answers/0", headers=bearer(stranger),
                          files={"file": ("a.webm", b"x", "video/webm")})).status_code == 404


async def test_interviews_get_a_private_video_room(hiring):
    when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r = await hiring["iv"].post(f"{API}/interviews", headers=bearer(hiring["admin"]), json={
        "application_id": hiring["app"], "scheduled_at": when, "interviewer_email": "boss@acme.io"})
    assert r.status_code == 201, r.text
    link = r.json()["meeting_link"]
    assert link.startswith("https://meet.jit.si/aihr-") and len(link) > 35


async def test_nepali_answers_get_an_english_version_for_hr(hiring, monkeypatch):
    async def transcribe(data, filename, content_type, language=None):
        return "म डिजाइन प्रणाली बनाउन मन पराउँछु र Figma मा काम गर्छु"

    async def english(text):
        return "I love building design systems and I work in Figma"

    reviewed = {}

    async def review(job, questions, transcripts):
        reviewed["transcripts"] = transcripts
        return screening_ai.Review(score=70, recommendation="pass", feedback="Relevant.")

    monkeypatch.setattr(screening_ai, "transcribe", transcribe)
    monkeypatch.setattr(screening_ai, "english_version", english)
    monkeypatch.setattr(screening_ai, "review_video_answers", review)
    iv, admin, cand, app = hiring["iv"], hiring["admin"], hiring["cand"], hiring["app"]
    screen = (await iv.post(f"{API}/screening/applications/{app}/video", json={"questions": ["Why this job?"]},
                            headers=bearer(admin))).json()
    await iv.post(f"{API}/screening/video/{screen['id']}/answers/0", headers=bearer(cand),
                  files={"file": ("a.webm", b"x", "video/webm")})
    await iv.post(f"{API}/screening/video/{screen['id']}/complete", headers=bearer(cand))
    answer = (await iv.get(f"{API}/screening/applications/{app}", headers=bearer(admin))).json()["video_screens"][0]["answers"][0]
    assert answer["transcript"].startswith("म डिजाइन") and answer["english"].startswith("I love building")
    assert reviewed["transcripts"] == ["I love building design systems and I work in Figma"]


async def test_english_version_only_for_nepali_text():
    assert await screening_ai.english_version("I built the design system.") is None


async def test_the_answer_language_is_passed_to_transcription(hiring, monkeypatch):
    heard = []

    async def transcribe(data, filename, content_type, language=None):
        heard.append(language)
        return "मैले डिजाइन प्रणाली बनाएँ र प्रयोगकर्ता अनुसन्धान गरेँ"

    async def nothing(*_a, **_k):
        return None

    monkeypatch.setattr(screening_ai, "transcribe", transcribe)
    monkeypatch.setattr(screening_ai, "english_version", nothing)
    monkeypatch.setattr(screening_ai, "review_video_answers", nothing)
    iv, admin, cand, app = hiring["iv"], hiring["admin"], hiring["cand"], hiring["app"]
    screen = (await iv.post(f"{API}/screening/applications/{app}/video", json={"questions": ["A?", "B?"]},
                            headers=bearer(admin))).json()
    for i, lang in enumerate(("ne", "")):
        r = await iv.post(f"{API}/screening/video/{screen['id']}/answers/{i}", headers=bearer(cand), data={"language": lang},
                          files={"file": ("a.webm", b"x", "video/webm")})
        assert r.status_code == 204, r.text
    assert (await iv.post(f"{API}/screening/video/{screen['id']}/answers/0", headers=bearer(cand),
                          data={"language": "xx"}, files={"file": ("a.webm", b"x", "video/webm")})).status_code == 422
    await iv.post(f"{API}/screening/video/{screen['id']}/complete", headers=bearer(cand))
    assert heard == ["ne", None]
