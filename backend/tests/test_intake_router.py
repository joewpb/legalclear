"""Unit tests for the /api/intake outage-swallow fix (AUDIT_FINDINGS.md S3-5a).

Both LLM attempts failing must surface as a non-200 response, never a
200 `module="unknown"` that looks like a valid classification.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from src.api.routes import app
from src.api.routers import intake
from src.core.upl import apply_disclaimer

client = TestClient(app)


class _FailingMessages:
    async def create(self, *args, **kwargs):
        raise RuntimeError("upstream outage")


def test_total_llm_failure_returns_error_not_200(monkeypatch):
    monkeypatch.setattr(intake._client, "messages", _FailingMessages())

    resp = client.post("/api/intake", json={"situation": "my landlord won't fix the AC"})

    assert resp.status_code == 503


def test_successful_classification_still_returns_200(monkeypatch):
    class _Response:
        content = [
            type(
                "Block",
                (),
                {
                    "text": (
                        '{"module": "small_claims", "sub_type": null, '
                        '"entities": {}, "confidence": 0.95, '
                        '"clarifying_question": null}'
                    )
                },
            )()
        ]

    class _OkMessages:
        async def create(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(intake._client, "messages", _OkMessages())

    resp = client.post("/api/intake", json={"situation": "small claims dispute over $500"})

    assert resp.status_code == 200
    assert resp.json()["module"] == "small_claims"


def test_disclaimer_matches_canonical_apply_disclaimer(monkeypatch):
    """B4b-6: intake.py now sources its disclaimer directly from
    src.core.upl.apply_disclaimer instead of src.core.disclaimer.get_disclaimer.
    Assert equality with apply_disclaimer's own output (not literal text) so
    this survives the B4b-1 canonicalization merge."""

    class _Response:
        content = [
            type(
                "Block",
                (),
                {
                    "text": (
                        '{"module": "small_claims", "sub_type": null, '
                        '"entities": {}, "confidence": 0.95, '
                        '"clarifying_question": null}'
                    )
                },
            )()
        ]

    class _OkMessages:
        async def create(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(intake._client, "messages", _OkMessages())

    resp = client.post(
        "/api/intake",
        json={"situation": "small claims dispute over $500", "language": "en"},
    )

    assert resp.status_code == 200
    expected = apply_disclaimer({}, lang="en", level="standard")["disclaimer"]
    assert resp.json()["disclaimer"] == expected


def test_disclaimer_language_behavior_preserved(monkeypatch):
    """Spanish requests must still get the Spanish disclaimer, matching
    pre-swap behavior."""

    class _Response:
        content = [
            type(
                "Block",
                (),
                {
                    "text": (
                        '{"module": "small_claims", "sub_type": null, '
                        '"entities": {}, "confidence": 0.95, '
                        '"clarifying_question": null}'
                    )
                },
            )()
        ]

    class _OkMessages:
        async def create(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(intake._client, "messages", _OkMessages())

    resp = client.post(
        "/api/intake",
        json={"situation": "disputa de reclamos menores por $500", "language": "es"},
    )

    assert resp.status_code == 200
    expected = apply_disclaimer({}, lang="es", level="standard")["disclaimer"]
    assert resp.json()["disclaimer"] == expected
