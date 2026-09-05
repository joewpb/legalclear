"""Phase A — police_report_v2 SSE protocol pins.

analyze_stream must emit ONLY complete typed SSE frames:
- every frame carries an ``event:`` name from the allowed set
- every ``data:`` payload is complete JSON (zero raw token fragments)
- the analysis JSON arrives as ONE ``analysis_json`` frame
- error paths emit a typed ``event: error`` frame, never bare data lines
- degraded ladder parses emit an error frame instead of ending silently
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.police_report_v2 import PoliceReportAnalyzerV2
from src.core.disclaimer import get_disclaimer

ALLOWED_EVENTS = {
    "progress",
    "analysis_json",
    "risk_analysis",
    "relevant_opinions",
    "case_context",
    "error",
}


class _FakeStream:
    """Mimics AsyncAnthropic messages.stream() async context manager."""

    def __init__(self, chunks):
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def _gen():
            for c in self._chunks:
                yield c
        return _gen()


class _FakeMessages:
    def __init__(self, chunks):
        self._chunks = chunks

    def stream(self, **kwargs):
        return _FakeStream(self._chunks)

    async def create(self, **kwargs):
        raise AssertionError("ladder retry must not fire for valid JSON")


class _FakeClient:
    def __init__(self, chunks):
        self.messages = _FakeMessages(chunks)


class _FakeParser:
    def __init__(self, raw_text="MOCK police report narrative text."):
        self._raw_text = raw_text

    async def extract_from_bytes_async(self, file_bytes):
        return {"raw_text": self._raw_text}


async def _fake_extract_case_context(docs):
    return {"routing": None}


def _parse_frames(body: str) -> list[tuple[str, dict]]:
    """Parse the raw SSE body into (event_name, payload) pairs.

    Raises on any frame without an event name or any unparseable data line —
    the exact invariants Phase A pins.
    """
    frames = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
        assert event is not None, f"frame without event name: {block[:80]!r}"
        assert data is not None, f"frame without data line: {block[:80]!r}"
        frames.append((event, json.loads(data)))
    return frames


def _analysis_json() -> str:
    return json.dumps({
        "incident_summary": "Traffic stop with consent search.",
        "parties": ["Subject", "Ofc. Harmon"],
        "charges_explained": [
            {"charge": "F.S. 893.13", "plain_english": "possession"}
        ],
        "miranda_noted": True,
        "probable_cause_present": True,
        "probable_cause_summary": "citizen tip",
        "discrepancies": [
            {
                "severity": "high",
                "defect_category": "fourth_amendment",
                "description": "coercive consent framing",
                "ask_attorney": "question?",
                "page_ref": "p.1",
            }
        ],
        "missing_fields": [],
        "what_happens_next": "review",
        "disclaimer": "llm disclaimer",
    })


def _make_analyzer(chunks, monkeypatch, raw_text="MOCK police report narrative text."):
    analyzer = PoliceReportAnalyzerV2.__new__(PoliceReportAnalyzerV2)
    analyzer.client = _FakeClient(chunks)
    analyzer.model = "claude-sonnet-4-6"
    analyzer._pdf_parser = _FakeParser(raw_text)
    monkeypatch.setattr(
        "src.agents.police_report_v2.get_relevant_opinions",
        lambda tags, limit=3, analysis_result=None: [],
    )
    monkeypatch.setattr(
        "src.agents.police_report_v2.generate_attorney_questions",
        lambda parsed, opinions: opinions,
    )
    monkeypatch.setattr(
        "src.agents.scanner.extract_case_context",
        _fake_extract_case_context,
    )
    return analyzer


def _run(agen):
    return asyncio.run(_collect(agen))


async def _collect(agen):
    return [chunk async for chunk in agen]


def test_success_path_emits_only_complete_typed_frames(monkeypatch):
    """Multi-token LLM output must arrive as ONE analysis_json frame."""
    payload = _analysis_json()
    half = len(payload) // 2
    chunks = [payload[:half], payload[half:]]  # two raw token chunks
    analyzer = _make_analyzer(chunks, monkeypatch)

    body = "".join(_run(analyzer.analyze_stream(b"pdf-bytes", "report.pdf", "en")))
    frames = _parse_frames(body)  # raises on unnamed/unparseable frames

    events = [e for e, _ in frames]
    assert all(e in ALLOWED_EVENTS for e in events), events

    # No per-token fragments: bounded, protocol-shaped frame count.
    assert len(frames) <= 7, f"{len(frames)} frames: {events}"

    # Stage heartbeats present.
    stages = [d["stage"] for e, d in frames if e == "progress"]
    assert stages == ["analyzing", "retrieving_case_law"], stages

    # Exactly one of each typed event.
    for want in ("analysis_json", "risk_analysis", "relevant_opinions",
                 "case_context"):
        assert events.count(want) == 1, (want, events)

    # The analysis JSON is the COMPLETE payload, one frame.
    aj = dict(frames[events.index("analysis_json")][1])
    assert aj["incident_summary"] == "Traffic stop with consent search."
    assert aj["miranda_noted"] is True
    assert aj["miranda_validity_concern"] is False  # Phase E flag present
    assert aj["discrepancies"][0]["defect_category"] == "fourth_amendment"
    # Deterministic disclaimer override (matches analyze()).
    assert aj["disclaimer"] == get_disclaimer("en")

    # Typed payloads carry their type discriminator.
    risk = dict(frames[events.index("risk_analysis")][1])
    assert risk["type"] == "risk_analysis"
    # One high finding = score 3 → MEDIUM band (compute_risk_score).
    assert risk["risk_score"] == 3
    assert risk["risk_level"] == "MEDIUM"
    opinions = dict(frames[events.index("relevant_opinions")][1])
    assert opinions["type"] == "relevant_opinions"
    assert opinions["opinions"] == []
    ctx = dict(frames[events.index("case_context")][1])
    assert ctx["type"] == "case_context"
    assert ctx["case_context"] == {"routing": None}


def test_unsupported_file_type_emits_typed_error(monkeypatch):
    analyzer = _make_analyzer([], monkeypatch)
    body = "".join(_run(analyzer.analyze_stream(b"x", "report.txt", "en")))
    frames = _parse_frames(body)
    assert len(frames) == 1
    event, data = frames[0]
    assert event == "error"
    assert data["type"] == "error"
    assert data["error"] is True
    assert "Unsupported file type" in data["message"]


def _long_analysis_json() -> str:
    """Valid analysis JSON whose text exceeds the heartbeat char cadence."""
    payload = json.loads(_analysis_json())
    payload["discrepancies"][0]["description"] = (
        "coercive consent framing " * 300
    )
    return json.dumps(payload)


def test_long_stream_emits_char_heartbeats_without_content(monkeypatch):
    """Steady token flow > 2000 chars must keep the wire busy with typed
    progress heartbeats that leak ZERO content (only counts)."""
    payload = _long_analysis_json()
    half = len(payload) // 2
    analyzer = _make_analyzer([payload[:half], payload[half:]], monkeypatch)

    body = "".join(_run(analyzer.analyze_stream(b"pdf-bytes", "report.pdf", "en")))
    frames = _parse_frames(body)
    events = [e for e, _ in frames]

    heartbeats = [
        d for e, d in frames
        if e == "progress" and d.get("stage") == "analyzing"
    ]
    assert len(heartbeats) >= 2  # start + at least one char-cadence beat
    for hb in heartbeats:
        assert set(hb.keys()) <= {"type", "stage", "chars"}
        if "chars" in hb:
            assert isinstance(hb["chars"], int)

    # The analysis JSON still arrives complete and intact.
    aj = dict(frames[events.index("analysis_json")][1])
    assert aj["incident_summary"] == "Traffic stop with consent search."
    assert len(aj["discrepancies"][0]["description"]) > 2000
    assert "error" not in events


class _SlowStream(_FakeStream):
    """Fake stream that stalls between chunks (simulates a slow LLM)."""

    def __init__(self, chunks, delay):
        super().__init__(chunks)
        self._delay = delay

    @property
    def text_stream(self):
        async def _gen():
            for c in self._chunks:
                await asyncio.sleep(self._delay)
                yield c
        return _gen()


class _SlowMessages(_FakeMessages):
    def __init__(self, chunks, delay):
        super().__init__(chunks)
        self._delay = delay

    def stream(self, **kwargs):
        return _SlowStream(self._chunks, self._delay)


def test_stall_emits_timer_heartbeat_and_completes(monkeypatch):
    """A token stall longer than the heartbeat window must emit a typed
    heartbeat WITHOUT cancelling the stream — the analysis still lands."""
    monkeypatch.setattr(
        "src.agents.police_report_v2._HEARTBEAT_SECONDS", 0.2,
    )
    payload = _analysis_json()
    analyzer = _make_analyzer([], monkeypatch)
    analyzer.client = type("SlowClient", (), {
        "messages": _SlowMessages([payload], delay=0.5),
    })()

    body = "".join(_run(analyzer.analyze_stream(b"x", "report.pdf", "en")))
    frames = _parse_frames(body)
    events = [e for e, _ in frames]
    assert "analysis_json" in events  # the generator survives the stall
    stall_hbs = [
        d for e, d in frames
        if e == "progress" and d.get("stage") == "analyzing" and "chars" in d
    ]
    assert stall_hbs  # at least one timer heartbeat fired
    assert stall_hbs[0]["chars"] == 0  # nothing accumulated before it


def test_analysis_json_includes_citations_checked(monkeypatch):
    """Phase C1 hook: the emitted analysis carries the citations_checked
    log — empty when the statutes DB is unavailable, never absent."""
    from src.services import citation_validation as cv

    monkeypatch.setattr(cv.db, "client", None)
    payload = _analysis_json()
    analyzer = _make_analyzer([payload], monkeypatch)

    body = "".join(_run(analyzer.analyze_stream(b"pdf-bytes", "report.pdf", "en")))
    frames = _parse_frames(body)
    events = [e for e, _ in frames]
    aj = dict(frames[events.index("analysis_json")][1])
    assert "citations_checked" in aj
    assert aj["citations_checked"] == []


def test_empty_pdf_emits_typed_error(monkeypatch):
    analyzer = _make_analyzer([], monkeypatch, raw_text="   ")
    body = "".join(_run(analyzer.analyze_stream(b"x", "report.pdf", "en")))
    frames = _parse_frames(body)
    assert len(frames) == 1
    event, data = frames[0]
    assert event == "error"
    assert data["type"] == "error"
    assert "No readable text" in data["message"]


def test_degraded_parse_emits_typed_error(monkeypatch):
    """Decision 20 degrade path: an error frame, never a silent end."""

    async def _fake_ladder(*args, **kwargs):
        return (None, True)

    monkeypatch.setattr(
        "src.agents.police_report_v2.parse_llm_json_ladder", _fake_ladder,
    )
    analyzer = _make_analyzer(["this is not json"], monkeypatch)
    body = "".join(_run(analyzer.analyze_stream(b"x", "report.pdf", "en")))
    frames = _parse_frames(body)
    events = [e for e, _ in frames]
    assert "analysis_json" not in events
    assert events.count("error") == 1
    assert dict(frames[-1][1])["type"] == "error"


def test_stream_error_emits_typed_error(monkeypatch):
    """Upstream failure inside the Claude stream → typed error frame."""

    class _ExplodingStream(_FakeStream):
        async def _gen(self):
            raise RuntimeError("upstream failure")
            yield  # pragma: no cover

        @property
        def text_stream(self):
            return self._gen()

    class _ExplodingMessages(_FakeMessages):
        def stream(self, **kwargs):
            return _ExplodingStream([])

    analyzer = _make_analyzer([], monkeypatch)
    analyzer.client = type(
        "ExplodingClient", (), {"messages": _ExplodingMessages([])}
    )()
    body = "".join(_run(analyzer.analyze_stream(b"x", "report.pdf", "en")))
    frames = _parse_frames(body)
    # progress(analyzing) may or may not precede the error frame; the
    # terminal frame must be the typed error.
    event, data = frames[-1]
    assert event == "error"
    assert data["type"] == "error"
    assert "Analysis could not be completed" in data["message"]
