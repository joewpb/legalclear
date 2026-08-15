"""B4b-4 — discovery_motion.py disclaimer: typed SSE event on success + error paths.

Pins that DiscoveryMotionAnalyzer.analyze_stream emits a typed
``event: disclaimer`` SSE frame on both the normal completion path and every
mid-stream error exit (PDF extraction failure, unreadable text, unsupported
file type, and the top-level stream exception), while leaving the embedded
``disclaimer`` field inside each error frame unchanged (backward compat).
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.discovery_motion import DiscoveryMotionAnalyzer
from src.core.disclaimer import get_disclaimer


class _FakeStream:
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


def _new_analyzer(text=None, raise_on_iter=False):
    analyzer = DiscoveryMotionAnalyzer.__new__(DiscoveryMotionAnalyzer)
    analyzer.client = _FakeClient(text, raise_on_iter)
    analyzer.model = "claude-sonnet-4-6"
    return analyzer


def test_analyze_stream_success_emits_typed_disclaimer():
    analyzer = _new_analyzer(text="this is not valid json")

    events = asyncio.run(
        _collect(analyzer.analyze_stream(b"fake-bytes", "motion.jpg", "en"))
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}


def test_analyze_stream_unsupported_file_emits_typed_disclaimer():
    analyzer = _new_analyzer()

    events = asyncio.run(
        _collect(analyzer.analyze_stream(b"fake-bytes", "motion.exe", "en"))
    )
    body = "".join(events)

    assert "event: disclaimer" in body
    expected = get_disclaimer("en")
    frame = _extract_frame(body, "disclaimer")
    assert json.loads(frame) == {"disclaimer": expected}

    assert '"error": true' in body
    error_payload = json.loads(body.split("\n\n")[1][len("data: "):])
    assert error_payload["disclaimer"] == expected


def test_analyze_stream_upstream_error_emits_typed_disclaimer():
    analyzer = _new_analyzer(raise_on_iter=True)

    events = asyncio.run(
        _collect(analyzer.analyze_stream(b"fake-bytes", "motion.jpg", "en"))
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
