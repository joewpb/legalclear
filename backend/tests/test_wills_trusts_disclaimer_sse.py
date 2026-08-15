"""B4b-5 — wills_trusts.py disclaimer: typed SSE event on success + error paths.

Pins that WillsTrustsExplainer.explain emits a typed ``event: disclaimer``
SSE frame on both the normal completion path and the mid-stream error path,
while leaving the embedded ``disclaimer`` field inside the JSON
payload/error frame unchanged (backward compat with older clients).
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.wills_trusts import WillsTrustsExplainer
from src.core.disclaimer import get_disclaimer


class _FakeStream:
    """Mimics the AsyncAnthropic `messages.stream(...)` async context manager."""

    def __init__(self, text: str = None, raise_on_iter: bool = False) -> None:
        self._text = text
        self._raise_on_iter = raise_on_iter

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def _gen(self):
        if self._raise_on_iter:
            raise RuntimeError("upstream failure")
        yield self._text

    @property
    def text_stream(self):
        return self._gen()


class _FakeMessages:
    def __init__(self, text: str = None, raise_on_iter: bool = False) -> None:
        self._text = text
        self._raise_on_iter = raise_on_iter

    def stream(self, **kwargs):
        return _FakeStream(self._text, self._raise_on_iter)


class _FakeClient:
    def __init__(self, text: str = None, raise_on_iter: bool = False) -> None:
        self.messages = _FakeMessages(text, raise_on_iter)


async def _collect(agen):
    return [chunk async for chunk in agen]


def _extract_frame(body: str, event_name: str) -> str:
    marker = f"event: {event_name}\ndata: "
    start = body.index(marker) + len(marker)
    end = body.index("\n\n", start)
    return body[start:end]


def _new_explainer(text=None, raise_on_iter=False):
    explainer = WillsTrustsExplainer.__new__(WillsTrustsExplainer)
    explainer.client = _FakeClient(text, raise_on_iter)
    explainer.model = "claude-sonnet-4-6"
    return explainer


def test_explain_success_emits_typed_disclaimer():
    explainer = _new_explainer(text="this is not valid json")

    events = asyncio.run(
        _collect(
            explainer.explain(
                situation="I want to write a will",
                sub_type="will",
                language="en",
            )
        )
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}


def test_explain_error_emits_typed_disclaimer():
    explainer = _new_explainer(raise_on_iter=True)

    events = asyncio.run(
        _collect(
            explainer.explain(
                situation="I want to write a will",
                sub_type="will",
                language="en",
            )
        )
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}

    # Terminal error frame is still present with disclaimer embedded (compat).
    assert '"error": true' in body
    error_line = [
        line for line in body.split("\n\n") if line.startswith("data: ") and "error" in line
    ][-1]
    error_payload = json.loads(error_line[len("data: "):])
    assert error_payload["disclaimer"] == expected
