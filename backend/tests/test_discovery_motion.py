"""Discovery Motion Analyzer — risk-score parse failure must not vanish silently."""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.discovery_motion import DiscoveryMotionAnalyzer


class _FakeStream:
    """Mimics the AsyncAnthropic `messages.stream(...)` async context manager."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def _gen(self):
        yield self._text

    @property
    def text_stream(self):
        return self._gen()


class _FakeMessages:
    def __init__(self, text: str) -> None:
        self._text = text

    def stream(self, **kwargs):
        return _FakeStream(self._text)

    async def create(self, **kwargs):
        # Decision 20 retry call — return the same garbage so the ladder
        # exhausts its one retry and degrades.
        return _FakeResp(self._text)


class _FakeResp:
    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def content(self):
        return [type("_C", (), {"text": self._text})()]


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.messages = _FakeMessages(text)


async def _collect(agen):
    return [chunk async for chunk in agen]


def test_risk_score_parse_failure_logs_error(caplog):
    """A malformed model completion must log the Decision 20 degrade marker,
    not vanish silently (and never emit a fake risk payload)."""
    analyzer = DiscoveryMotionAnalyzer.__new__(DiscoveryMotionAnalyzer)
    analyzer.client = _FakeClient("this is not valid json")
    analyzer.model = "claude-sonnet-4-6"

    with caplog.at_level(logging.WARNING, logger="src.core.json_utils"):
        events = asyncio.run(
            _collect(analyzer.analyze_stream(b"fake-bytes", "motion.jpg", "en"))
        )

    assert not any('"type": "risk_analysis"' in e for e in events)
    assert any(
        "LLM_PARSE_DEGRADE" in r.message and "site=discovery_motion" in r.message
        for r in caplog.records
    )
