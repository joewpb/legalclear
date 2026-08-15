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


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.messages = _FakeMessages(text)


async def _collect(agen):
    return [chunk async for chunk in agen]


def test_risk_score_parse_failure_logs_error(caplog):
    """A malformed model completion must log at error, not vanish silently."""
    analyzer = DiscoveryMotionAnalyzer.__new__(DiscoveryMotionAnalyzer)
    analyzer.client = _FakeClient("this is not valid json")
    analyzer.model = "claude-sonnet-4-6"

    with caplog.at_level(logging.ERROR, logger="src.agents.discovery_motion"):
        events = asyncio.run(
            _collect(analyzer.analyze_stream(b"fake-bytes", "motion.jpg", "en"))
        )

    assert not any('"type": "risk_analysis"' in e for e in events)
    assert any("risk-score parse failed" in r.message for r in caplog.records)
