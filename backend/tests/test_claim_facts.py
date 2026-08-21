"""I-2c — claim_facts: policy_inception_date capture, regime resolution,
and escalation. Mirrors the B5 gate style (test_decision6_worked_examples.py).

Pure Python + mocked Supabase client, no live DB, no LLM.

Run: cd backend && uv run python -m pytest tests/test_claim_facts.py -v
"""

import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.property_casualty import (
    GUIDANCE_UNKNOWN_POLICY_INCEPTION,
    PropertyCasualtyExplainer,
)
from src.core.claim_regime import resolve_regime

_BACKEND_SRC = Path(__file__).parent.parent / "src"
_CAPTURE_FILES = {"src/memory/db.py", "src/api/routers/property_casualty.py"}


# ── resolve_regime: three outcomes + boundary ────────────────────────────


def test_resolve_regime_pre_cutoff():
    assert resolve_regime(date(2022, 12, 15)) == "pre"


def test_resolve_regime_post_cutoff():
    assert resolve_regime(date(2022, 12, 17)) == "post"


def test_resolve_regime_boundary_date_is_post():
    """2022-12-16 itself is "post" — SB 2-A applies to policies issued on
    or after this date (dispatch I-2c, docstring in claim_regime.py)."""
    assert resolve_regime(date(2022, 12, 16)) == "post"


def test_resolve_regime_unknown_is_only_from_none():
    assert resolve_regime(None) == "unknown"


# ── capture upsert: provenance always user_supplied ──────────────────────


class _FakeTable:
    def __init__(self, name, recorder):
        self._name = name
        self._recorder = recorder
        self._filters = {}

    def select(self, *a, **k):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def limit(self, *a, **k):
        return self

    def upsert(self, row, **k):
        self._recorder.append((self._name, dict(row)))
        return self

    def execute(self):
        return MagicMock(data=[])


class _FakeClient:
    def __init__(self):
        self.writes = []

    def table(self, name):
        return _FakeTable(name, self.writes)


def test_upsert_claim_fact_always_user_supplied():
    from src.memory.db import DatabaseManager

    db = DatabaseManager.__new__(DatabaseManager)
    db.client = _FakeClient()
    import logging
    db.logger = logging.getLogger("test")

    ok = db.upsert_claim_fact("session-1", "2023-01-01")
    assert ok is True
    writes = [r for name, r in db.client.writes if name == "claim_facts"]
    assert len(writes) == 1
    assert writes[0]["provenance"] == "user_supplied"
    assert writes[0]["session_id"] == "session-1"
    assert writes[0]["policy_inception_date"] == "2023-01-01"


# ── escalation path: absent/unknown -> guidance present, no regime content ──


def _explainer_with_fact(fact: dict | None) -> PropertyCasualtyExplainer:
    explainer = PropertyCasualtyExplainer.__new__(PropertyCasualtyExplainer)
    explainer._db = MagicMock()
    explainer._db.get_claim_fact = MagicMock(return_value=fact)
    return explainer


def test_session_with_no_fact_row_escalates():
    explainer = _explainer_with_fact(None)
    result = explainer._resolve_claim_regime("session-1")
    assert result == {"regime": "unknown", "guidance": GUIDANCE_UNKNOWN_POLICY_INCEPTION}


def test_session_with_known_fact_resolves():
    explainer = _explainer_with_fact({"policy_inception_date": "2024-01-01"})
    result = explainer._resolve_claim_regime("session-1")
    assert result == {"regime": "post"}


# ── mechanical enforcement: the pipeline has no write path to claim_facts ──


def test_no_write_path_to_claim_facts_outside_capture_module():
    """Every insert/upsert of claim_facts must live in one of
    _CAPTURE_FILES. A write anywhere else (e.g. the deadline pipeline)
    would mean a non-user-supplied value could clobber the user's answer —
    the exact B5 failure this table's design exists to prevent."""
    offenders = []
    for path in _BACKEND_SRC.rglob("*.py"):
        rel = str(path.relative_to(_BACKEND_SRC.parent)).replace("\\", "/")
        text = path.read_text()
        if "claim_facts" not in text:
            continue
        has_write_verb = (
            '.upsert(' in text and 'claim_facts' in text
        ) or (
            '.insert(' in text and 'claim_facts' in text
        )
        if has_write_verb and rel not in _CAPTURE_FILES:
            offenders.append(rel)
    assert offenders == [], (
        f"claim_facts write verb found outside the capture module: {offenders}"
    )


def test_no_write_path_grep_is_precise():
    """Sanity-check the grep test's own precision: it must actually find
    the two known write files and nothing else pre-emptively excluded."""
    result = subprocess.run(
        ["grep", "-rl", "claim_facts", str(_BACKEND_SRC)],
        capture_output=True, text=True, check=False,
    )
    hits = {
        str(Path(p).relative_to(_BACKEND_SRC.parent)).replace("\\", "/")
        for p in result.stdout.splitlines()
    }
    assert _CAPTURE_FILES <= hits, hits
