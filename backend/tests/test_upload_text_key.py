"""S2-5a: /upload must store ingest_document's "cleaned_text" key, not a
nonexistent "text" key. Regression test for the mapping in
src/api/routes.py::upload_document.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api import routes  # noqa: E402


class _FakeRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self):
        return self._body


def test_upload_stores_cleaned_text():
    asyncio.run(_run_upload_stores_cleaned_text())


async def _run_upload_stores_cleaned_text():
    # Real ingest_document() return-dict shape — no "text" key.
    ingest_result = {
        "error": False,
        "raw_text": "raw",
        "cleaned_text": "the extracted document text",
        "page_count": 1,
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
        mock_classifier.get_price_tier = MagicMock(return_value={"tier": "free", "price_usd": 0})
        mock_escalation.route = MagicMock(return_value={"escalate": False})
        mock_db.get_user = MagicMock(return_value={"id": "user-1"})
        mock_db.create_session = MagicMock(return_value="session-1")
        mock_db.create_document = MagicMock(return_value="document-1")

        await routes.upload_document(
            request=_FakeRequest(b"%PDF-fake-bytes"),
            user_id="user-1",
            filename="doc.pdf",
            email="user@example.com",
            lang="en",
        )

        mock_db.create_document.assert_called_once_with(
            "session-1", "the extracted document text"
        )
