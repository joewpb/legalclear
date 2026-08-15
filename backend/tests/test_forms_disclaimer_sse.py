"""B4b-3 — forms.py disclaimer: untyped chunk -> typed SSE event.

Pins that /api/forms/suggest emits the disclaimer as a typed `event:
disclaimer` SSE frame (not a bare `data:` chunk), on both the empty-candidates
path and the normal streaming path, while leaving every other chunk in the
same stream (text chunks, [DONE] sentinel) untyped/unchanged.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "testkey123")

from fastapi.testclient import TestClient

from src.api.routers import forms as forms_router
from src.api.routes import app
from src.core.disclaimer import get_disclaimer

client = TestClient(app)


class _FakeDB:
    def __init__(self):
        self.client = object()  # only truthiness/None-check matters here


def test_suggest_forms_empty_candidates_emits_typed_disclaimer(monkeypatch):
    monkeypatch.setattr(forms_router, "db", _FakeDB())
    monkeypatch.setattr(
        forms_router, "_candidate_forms_for_situation", lambda situation, limit=10: []
    )

    r = client.post(
        "/api/forms/suggest",
        json={"situation": "something with no matching forms"},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    body = r.text

    assert "event: disclaimer" in body
    expected_disclaimer = get_disclaimer(lang="en")
    disclaimer_frame = _extract_frame(body, "disclaimer")
    assert json.loads(disclaimer_frame) == {"disclaimer": expected_disclaimer}

    # The text chunk before it and the [DONE] sentinel after are unaffected.
    assert '"text":' in body
    assert "data: [DONE]" in body
    assert "event: disclaimer\ndata: [DONE]" not in body


def test_suggest_forms_stream_emits_typed_disclaimer(monkeypatch):
    monkeypatch.setattr(forms_router, "db", _FakeDB())
    monkeypatch.setattr(
        forms_router,
        "_candidate_forms_for_situation",
        lambda situation, limit=10: [
            {
                "form_number": "12.900(a)",
                "title": "Petition",
                "category": "family",
                "situation_tags": ["divorce"],
                "plain_language_summary": "Starts a case.",
            }
        ],
    )

    class _FakeTextStream:
        def __aiter__(self):
            async def gen():
                for chunk in ["Form 12.900(a) may apply."]:
                    yield chunk

            return gen()

    class _FakeStreamCtx:
        text_stream = _FakeTextStream()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    def _fake_stream(*args, **kwargs):
        return _FakeStreamCtx()

    monkeypatch.setattr(forms_router._anthropic.messages, "stream", _fake_stream)
    monkeypatch.setattr(
        forms_router, "apply_upl_guardrails", lambda text, lang: text
    )

    r = client.post(
        "/api/forms/suggest",
        json={"situation": "I need to file for divorce"},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    body = r.text

    assert "event: disclaimer" in body
    expected_disclaimer = get_disclaimer(lang="en")
    disclaimer_frame = _extract_frame(body, "disclaimer")
    assert json.loads(disclaimer_frame) == {"disclaimer": expected_disclaimer}

    # The AI text chunk is untouched (still a bare data: chunk, not typed).
    assert '"text": "Form 12.900(a) may apply."' in body
    assert "data: [DONE]" in body


def _extract_frame(body: str, event_name: str) -> str:
    """Pull the `data:` payload for a given `event:` frame out of raw SSE text."""
    marker = f"event: {event_name}\ndata: "
    start = body.index(marker) + len(marker)
    end = body.index("\n\n", start)
    return body[start:end]


# ── Decision 5 — error exits ────────────────────────────────────────────────
#
# forms.py has three error exits out of /api/forms/suggest:
#   1. db.client is None (line ~506)              -> HTTPException, no content ever emitted
#   2. _candidate_forms_for_situation raises (511) -> HTTPException, no content ever emitted
#   3. the Anthropic stream raises mid-generation  -> SSE error frame, content may
#      already have been streamed to the client
#
# Decision 5: an error with no prior substantive content needs no disclaimer;
# an error that can occur after substantive content has been emitted must
# carry one. Exits 1-2 never reach the SSE body at all (pre-content, no
# disclaimer required or present). Exit 3 already embeds `disclaimer` as a
# field on the untyped error payload, which satisfies "carries the
# disclaimer" for an after-content exit without needing a typed frame.


def test_suggest_forms_db_unavailable_error_has_no_disclaimer(monkeypatch):
    monkeypatch.setattr(forms_router, "db", _FakeDB())
    forms_router.db.client = None

    r = client.post(
        "/api/forms/suggest",
        json={"situation": "anything"},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 503
    assert "disclaimer" not in r.text.lower()


def test_suggest_forms_candidate_search_error_has_no_disclaimer(monkeypatch):
    monkeypatch.setattr(forms_router, "db", _FakeDB())

    def _boom(situation, limit=10):
        raise RuntimeError("search backend down")

    monkeypatch.setattr(forms_router, "_candidate_forms_for_situation", _boom)

    r = client.post(
        "/api/forms/suggest",
        json={"situation": "anything"},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 500
    assert "disclaimer" not in r.text.lower()


def test_suggest_forms_stream_error_embeds_disclaimer_field(monkeypatch):
    monkeypatch.setattr(forms_router, "db", _FakeDB())
    monkeypatch.setattr(
        forms_router,
        "_candidate_forms_for_situation",
        lambda situation, limit=10: [
            {
                "form_number": "12.900(a)",
                "title": "Petition",
                "category": "family",
                "situation_tags": ["divorce"],
                "plain_language_summary": "Starts a case.",
            }
        ],
    )

    class _FakeTextStream:
        def __aiter__(self):
            async def gen():
                yield "Form 12.900(a) may apply."
                raise RuntimeError("connection dropped mid-stream")

            return gen()

    class _FakeStreamCtx:
        text_stream = _FakeTextStream()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(
        forms_router._anthropic.messages, "stream", lambda *a, **k: _FakeStreamCtx()
    )

    r = client.post(
        "/api/forms/suggest",
        json={"situation": "I need to file for divorce"},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    body = r.text

    # Substantive content (the AI text chunk) was already streamed before the
    # failure, so this error exit must carry the disclaimer.
    assert '"text": "Form 12.900(a) may apply."' in body
    assert '"error": true' in body
    expected_disclaimer = get_disclaimer(lang="en")
    assert json.dumps(expected_disclaimer) in body
    # No typed `event: disclaimer` frame is expected here -- the embedded
    # field on the error payload is the one required by Decision 5.
    assert "event: disclaimer" not in body
