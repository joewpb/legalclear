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
