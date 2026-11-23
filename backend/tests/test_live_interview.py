"""The in-app interview: room access, call setup messages, recording consent, transcript, notes and scorecard."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from shared.db.session import AsyncSessionLocal
from shared.models.entities import Notification
from shared.services import interview_ai, screening_ai
from tests.conftest import bearer, signup
from tests.test_saas import make_candidate
from tests.test_screening import _emails, hiring  # noqa: F401

API = "/api/v1"


@pytest.fixture
async def call(hiring):  # noqa: F811
    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    iv = await hiring["iv"].post(f"{API}/interviews", headers=bearer(hiring["admin"]), json={
        "application_id": hiring["app"], "scheduled_at": when, "interviewer_email": "boss@acme.io"})
    assert iv.status_code == 201, iv.text
    return {**hiring, "id": iv.json()["id"]}


async def test_the_invite_points_to_the_in_app_room(call):
    room = f"/interview/{call['id']}"
    sent = [s for r, s in await _emails("interview.scheduled")]
    assert len(sent) == 2
    async with AsyncSessionLocal() as db:
        bodies = (await db.execute(select(Notification.body).where(
            Notification.event_type == "interview.scheduled"))).scalars().all()
    assert all(room in b for b in bodies)
    assert any("recorded" in b and "your choice" in b for b in bodies)


async def test_both_sides_join_and_pass_call_setup_messages(call):
    iv, admin, cand, i = call["iv"], call["admin"], call["cand"], call["id"]
    staff_room = (await iv.post(f"{API}/interviews/{i}/room/join", headers=bearer(admin))).json()
    assert staff_room["role"] == "interviewer" and staff_room["ice_servers"]
    cand_room = (await iv.post(f"{API}/interviews/{i}/room/join", headers=bearer(cand))).json()
    assert cand_room["role"] == "candidate" and cand_room["prep_questions"] == []

    got = (await iv.get(f"{API}/interviews/{i}/room/signal?after={staff_room['cursor']}", headers=bearer(admin))).json()
    assert [m["kind"] for m in got["messages"]] == ["hello"]
    await iv.post(f"{API}/interviews/{i}/room/signal", headers=bearer(admin),
                  json={"kind": "offer", "data": {"sdp": "v=0", "type": "offer"}})
    got = (await iv.get(f"{API}/interviews/{i}/room/signal?after={cand_room['cursor']}", headers=bearer(cand))).json()
    assert [m["kind"] for m in got["messages"]] == ["offer"] and got["messages"][0]["data"]["sdp"] == "v=0"
    assert (await iv.post(f"{API}/interviews/{i}/room/signal", headers=bearer(cand),
                          json={"kind": "consent", "data": {}})).status_code == 409


async def test_strangers_cannot_enter(call):
    i = call["id"]
    other_company = (await signup(call["gw"], "Globex", "g@globex.io"))["access_token"]
    other_applicant = await make_candidate(call["gw"], "acme", "eve@acme.io")
    for token in (other_company, other_applicant):
        assert (await call["iv"].post(f"{API}/interviews/{i}/room/join", headers=bearer(token))).status_code == 404
    assert (await call["iv"].get(f"{API}/interviews/{i}", headers=bearer(call["cand"]))).status_code == 403


AUDIO = {"file": ("p.webm", b"\x1aE\xdf\xa3audio", "audio/webm;codecs=opus")}


async def _upload(iv, token, i, part, track, offset):
    return await iv.post(f"{API}/interviews/{i}/room/audio", headers=bearer(token), files=AUDIO,
                         data={"part": str(part), "track": track, "offset": str(offset), "language": "en"})


async def test_nothing_is_recorded_without_the_applicants_consent(call):
    iv, admin, cand, i = call["iv"], call["admin"], call["cand"], call["id"]
    assert (await iv.post(f"{API}/interviews/{i}/room/recording", headers=bearer(admin),
                          json={"on": True})).status_code == 409
    assert (await _upload(iv, admin, i, 0, "candidate", 0)).status_code == 409
    # Only the applicant can consent.
    assert (await iv.post(f"{API}/interviews/{i}/room/consent", headers=bearer(admin),
                          json={"allowed": True})).status_code == 403
    await iv.post(f"{API}/interviews/{i}/room/consent", headers=bearer(cand), json={"allowed": True})
    assert (await iv.post(f"{API}/interviews/{i}/room/recording", headers=bearer(admin),
                          json={"on": True})).status_code == 204
    assert (await _upload(iv, admin, i, 0, "candidate", 0)).status_code == 204

    # Withdrawing stops it, and the interviewer's browser hears about it right away.
    await iv.post(f"{API}/interviews/{i}/room/consent", headers=bearer(cand), json={"allowed": False})
    detail = (await iv.get(f"{API}/interviews/{i}", headers=bearer(admin))).json()
    assert detail["recording_consent"] is False and detail["recording_on"] is False
    assert (await _upload(iv, admin, i, 1, "candidate", 300)).status_code == 409
    got = (await iv.get(f"{API}/interviews/{i}/room/signal?after=0", headers=bearer(admin))).json()
    assert [m["data"] for m in got["messages"] if m["kind"] == "consent"] == [{"allowed": True}, {"allowed": False}]


async def test_after_the_call_both_speakers_are_transcribed_in_order_with_notes(call, monkeypatch):
    heard = {}

    async def transcribe_timed(data, filename, content_type, language=None):
        heard[filename] = language
        if "interviewer" in filename:
            return [(0.0, "Tell me about the API you built."), (40.0, "How did you test it?")]
        return [(5.0, "I built a FastAPI service for payments."), (45.0, "With pytest and contract tests.")]

    async def summarize(job, transcript):
        heard["summary_input"] = transcript
        return {"overview": "Solid backend experience.", "skills": [], "strengths": ["Testing"], "concerns": [],
                "follow_ups": [], "recommendation": "advance"}

    monkeypatch.setattr(screening_ai, "transcribe_timed", transcribe_timed)
    monkeypatch.setattr(interview_ai, "summarize", summarize)
    iv, admin, cand, i = call["iv"], call["admin"], call["cand"], call["id"]
    await iv.post(f"{API}/interviews/{i}/room/consent", headers=bearer(cand), json={"allowed": True})
    for track in ("interviewer", "candidate"):
        assert (await _upload(iv, admin, i, 0, track, 0)).status_code == 204
        assert (await _upload(iv, admin, i, 1, track, 300)).status_code == 204

    # Only the interviewer ends it.
    assert (await iv.post(f"{API}/interviews/{i}/room/end", headers=bearer(cand))).status_code == 403
    ended = (await iv.post(f"{API}/interviews/{i}/room/end", headers=bearer(admin))).json()
    assert ended["status"] == "completed"

    detail = (await iv.get(f"{API}/interviews/{i}", headers=bearer(admin))).json()
    assert detail["summary_status"] == "ready" and detail["summary"]["recommendation"] == "advance"
    lines = detail["transcript"]
    assert [(round(x["at"]), x["speaker"]) for x in lines[:4]] == [
        (0, "interviewer"), (5, "candidate"), (40, "interviewer"), (45, "candidate")]
    assert lines[-1]["at"] == 345.0 and detail["recorded_parts"] == 2
    assert len(lines) == 8
    assert heard["summary_input"].startswith("[00:00] Interviewer: Tell me about the API you built.\n[00:05] Applicant:")
    assert ("boss@acme.io", "Interview notes ready: Cand") in await _emails("interview.notes_ready")
    # The candidate's browser is told the call ended.
    got = (await iv.get(f"{API}/interviews/{i}/room/signal?after=0", headers=bearer(cand))).json()
    assert got["messages"][-1]["kind"] == "bye"


async def test_prep_questions_and_scorecard(call, monkeypatch):
    seen = {}

    async def prep(job, resume, screening):
        seen["job"] = job.title
        return [{"question": "Walk me through a model you shipped.", "why": "Tests the core requirement."}]

    monkeypatch.setattr(interview_ai, "prep_questions", prep)
    iv, admin, i = call["iv"], call["admin"], call["id"]
    detail = (await iv.post(f"{API}/interviews/{i}/prep", headers=bearer(admin))).json()
    assert detail["prep_questions"][0]["question"].startswith("Walk me through") and seen["job"]
    room = (await iv.post(f"{API}/interviews/{i}/room/join", headers=bearer(admin))).json()
    assert room["prep_questions"] == detail["prep_questions"]

    assert (await iv.put(f"{API}/interviews/{i}/scorecard", headers=bearer(admin),
                         json={"rating": 9, "recommendation": "advance"})).status_code == 422
    saved = (await iv.put(f"{API}/interviews/{i}/scorecard", headers=bearer(admin),
                          json={"rating": 4, "recommendation": "advance", "notes": " Strong on testing. "})).json()
    assert saved["scorecard"]["rating"] == 4 and saved["scorecard"]["notes"] == "Strong on testing."
    listed = (await iv.get(f"{API}/interviews?application_id={call['app']}", headers=bearer(admin))).json()
    assert [x["id"] for x in listed] == [i]
    mine = (await iv.get(f"{API}/interviews/mine", headers=bearer(call["cand"]))).json()
    assert mine[0]["id"] == i and mine[0]["status"] == "scheduled"


async def test_summary_says_so_when_there_is_too_little_speech():
    notes = await interview_ai.summarize(None, "[00:00] Applicant: hello there")
    assert notes["recommendation"] == "unsure" and "too little speech" in notes["overview"]


def test_transcript_formatting():
    text = interview_ai.format_transcript([{"at": 75.2, "speaker": "candidate", "text": "Yes."}])
    assert text == "[01:15] Applicant: Yes."


def test_back_to_back_pieces_from_one_speaker_become_one_turn():
    from shared.services.live_interview import merge_turns
    lines = [{"at": 0, "speaker": "interviewer", "text": "Why us?"},
             {"at": 4, "speaker": "candidate", "text": "I built"}, {"at": 9, "speaker": "candidate", "text": "the API."},
             {"at": 12, "speaker": "interviewer", "text": "Thanks."}]
    assert [(x["speaker"], x["text"]) for x in merge_turns(lines)] == [
        ("interviewer", "Why us?"), ("candidate", "I built the API."), ("interviewer", "Thanks.")]
