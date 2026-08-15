"""B4b-4 / B4e-a — criminal_procedure.py disclaimer: typed SSE event on
success + error paths.

Pins that CriminalProcedureExplainer.explain_stream emits a typed
``event: disclaimer`` SSE frame on the normal completion path and on any
error path that follows emitted content, while leaving the embedded
``disclaimer`` field inside the JSON payload/error frame unchanged (backward
compat with older clients). Per Decision 5, an error that fires before any
substantive content has been streamed carries no disclaimer event.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.criminal_procedure import CriminalProcedureExplainer
from src.core.disclaimer import get_disclaimer


class _FakeStream:
    """Mimics the AsyncAnthropic `messages.stream(...)` async context manager."""

    def __init__(
        self,
        text: str = None,
        raise_on_iter: bool = False,
        raise_after_chunk: bool = False,
    ) -> None:
        self._text = text
        self._raise_on_iter = raise_on_iter
        self._raise_after_chunk = raise_after_chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def _gen(self):
        if self._raise_on_iter:
            raise RuntimeError("upstream failure")
        if self._raise_after_chunk:
            yield self._text
            raise RuntimeError("upstream failure mid-stream")
        yield self._text

    @property
    def text_stream(self):
        return self._gen()


class _FakeMessages:
    def __init__(
        self,
        text: str = None,
        raise_on_iter: bool = False,
        raise_after_chunk: bool = False,
    ) -> None:
        self._text = text
        self._raise_on_iter = raise_on_iter
        self._raise_after_chunk = raise_after_chunk

    def stream(self, **kwargs):
        return _FakeStream(self._text, self._raise_on_iter, self._raise_after_chunk)


class _FakeClient:
    def __init__(
        self,
        text: str = None,
        raise_on_iter: bool = False,
        raise_after_chunk: bool = False,
    ) -> None:
        self.messages = _FakeMessages(text, raise_on_iter, raise_after_chunk)


async def _collect(agen):
    return [chunk async for chunk in agen]


def _extract_frame(body: str, event_name: str) -> str:
    marker = f"event: {event_name}\ndata: "
    start = body.index(marker) + len(marker)
    end = body.index("\n\n", start)
    return body[start:end]


def test_explain_stream_success_emits_typed_disclaimer():
    explainer = CriminalProcedureExplainer.__new__(CriminalProcedureExplainer)
    # Not valid JSON — skips opinion retrieval (best-effort, logged) without
    # touching the network/corpus; irrelevant to the disclaimer assertion.
    explainer.client = _FakeClient("this is not valid json")
    explainer.model = "claude-sonnet-4-6"

    events = asyncio.run(
        _collect(
            explainer.explain_stream(
                charge_type="petit theft",
                severity="misdemeanor",
                current_stage="arraigned",
                language="en",
            )
        )
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}


def test_explain_stream_error_before_content_omits_disclaimer():
    """Decision 5: error with no prior content carries no disclaimer event."""
    explainer = CriminalProcedureExplainer.__new__(CriminalProcedureExplainer)
    explainer.client = _FakeClient(raise_on_iter=True)
    explainer.model = "claude-sonnet-4-6"

    events = asyncio.run(
        _collect(
            explainer.explain_stream(
                charge_type="DUI",
                severity="misdemeanor",
                current_stage="charged",
                language="en",
            )
        )
    )
    body = "".join(events)

    assert "event: disclaimer" not in body

    # Terminal error frame is still present with disclaimer embedded (compat).
    expected = get_disclaimer("en")
    assert '"error": true' in body
    error_line = [
        line for line in body.split("\n\n") if line.startswith("data: ") and "error" in line
    ][-1]
    error_payload = json.loads(error_line[len("data: "):])
    assert error_payload["disclaimer"] == expected


def test_explain_stream_error_after_content_emits_typed_disclaimer():
    """Decision 5: error after substantive content still carries the disclaimer."""
    explainer = CriminalProcedureExplainer.__new__(CriminalProcedureExplainer)
    explainer.client = _FakeClient(text="partial content", raise_after_chunk=True)
    explainer.model = "claude-sonnet-4-6"

    events = asyncio.run(
        _collect(
            explainer.explain_stream(
                charge_type="DUI",
                severity="misdemeanor",
                current_stage="charged",
                language="en",
            )
        )
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}

    assert '"error": true' in body
    error_line = [
        line for line in body.split("\n\n") if line.startswith("data: ") and "error" in line
    ][-1]
    error_payload = json.loads(error_line[len("data: "):])
    assert error_payload["disclaimer"] == expected
