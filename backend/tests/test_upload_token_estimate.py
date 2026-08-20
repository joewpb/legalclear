"""B2-D3: ingest_document() never populated a "token_estimate" key, so
/upload always stored document_token_count=0 (both the persisted count and
classifier.get_price_tier's pricing tier). Regression test for
src/ingestion/__init__.py::ingest_document producing "token_estimate" and
src/api/routes.py::upload_document passing it through to db.create_session.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api import routes  # noqa: E402
import src.ingestion as ingestion_module  # noqa: E402
from src.ingestion import ingest_document  # noqa: E402


def _real_request(body: bytes) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/upload",
        "raw_path": b"/upload",
        "headers": [(b"x-api-key", b"test")],
        "query_string": b"",
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "state": {},
    }

    async def _receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive=_receive)


class _FakeRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self):
        return self._body


def test_ingest_document_populates_token_estimate():
    asyncio.run(_run_ingest_document_populates_token_estimate())


async def _run_ingest_document_populates_token_estimate():
    text = "word " * 100  # 100 words -> int(100 * 1.3) == 130 tokens

    with patch.object(
        ingestion_module._pdf,
        "extract_from_bytes_async",
        new=AsyncMock(return_value={"raw_text": text, "page_count": 1}),
    ):
        result = await ingest_document(b"%PDF-fake-bytes", "doc.pdf")

    assert result["error"] is False
    assert result["token_estimate"] == int(len(text.split()) * 1.3)


def test_upload_stores_real_token_estimate():
    asyncio.run(_run_upload_stores_real_token_estimate())


async def _run_upload_stores_real_token_estimate():
    ingest_result = {
        "error": False,
        "raw_text": "raw",
        "cleaned_text": "the extracted document text",
        "page_count": 1,
        "token_estimate": 4321,
        "filename": "doc.pdf",
        "ingestion_method": "pdf",
    }

    with (
        patch.object(routes, "ingest_document", new=AsyncMock(return_value=ingest_result)),
        patch.object(routes, "classifier") as mock_classifier,
        patch.object(routes, "escalation_router") as mock_escalation,
        patch.object(routes, "db") as mock_db,
    ):
        mock_classifier.classify = AsyncMock(return_value={"doc_type": "other"})
        mock_classifier.get_price_tier = MagicMock(return_value={"tier": "medium", "price_usd": 10})
        mock_escalation.route = MagicMock(return_value={"escalate": False})
        mock_db.get_user = MagicMock(return_value={"id": "user-1"})
        mock_db.create_session = MagicMock(return_value="session-1")
        mock_db.create_document = MagicMock(return_value="document-1")

        await routes.upload_document(
            request=_real_request(b"%PDF-fake-bytes"),
            user_id="user-1",
            filename="doc.pdf",
            email="user@example.com",
            lang="en",
        )

        _, kwargs = mock_db.create_session.call_args
        assert kwargs["token_count"] == 4321
