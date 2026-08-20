"""Tests for the P&C content schema + loader (Dispatch I-2a).

Pure Python — no network, no live Supabase calls. Authority resolution runs
against the P&C curated citation set in-process
(``src.agents.pc_citations.PC_CURATED_CITATIONS``), not a live DB.
"""

import json
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.content.loader import ContentLoadError, load_active_content
from src.content.models import ContentRecord

RESOLVABLE_CITATION = "Fla. Stat. § 627.70131"
UNRESOLVABLE_CITATION = "Fla. Stat. § 627.999"


def _minimal_record(**overrides) -> dict:
    record = {
        "phase_id": "fire.p0.test",
        "peril": ["fire"],
        "jurisdiction": "FL",
        "policy_inception_after": "any",
        "sequence": 1,
        "title": "Test phase",
        "plain_summary": "Plain summary text.",
        "authority": [RESOLVABLE_CITATION],
        "effective_date": "2023-03-24",
        "version": 1,
        "superseded_by": None,
    }
    record.update(overrides)
    return record


def _write_jsonl(data_dir, filename, records):
    path = data_dir / filename
    path.write_text("\n".join(json.dumps(r) for r in records))
    return path


# --- model-level validation -------------------------------------------------


def test_minimal_valid_record_loads():
    record = ContentRecord(**_minimal_record())
    assert record.phase_id == "fire.p0.test"
    assert record.authority == [RESOLVABLE_CITATION]


def test_record_missing_authority_fails():
    payload = _minimal_record()
    del payload["authority"]
    with pytest.raises(ValidationError):
        ContentRecord(**payload)


def test_record_missing_effective_date_fails():
    payload = _minimal_record()
    del payload["effective_date"]
    with pytest.raises(ValidationError):
        ContentRecord(**payload)


def test_never_do_missing_consequence_fails():
    payload = _minimal_record(
        never_do=[{"id": "n1", "text": "Do not sign a release."}]
    )
    with pytest.raises(ValidationError):
        ContentRecord(**payload)


def test_do_now_missing_why_fails():
    payload = _minimal_record(
        do_now=[{"id": "d1", "text": "Call your insurer."}]
    )
    with pytest.raises(ValidationError):
        ContentRecord(**payload)


def test_do_now_and_never_do_with_required_fields_load():
    payload = _minimal_record(
        do_now=[{"id": "d1", "text": "Call your insurer.", "why": "Starts the clock."}],
        never_do=[
            {
                "id": "n1",
                "text": "Do not sign a release.",
                "consequence": "You may waive your right to more money.",
            }
        ],
    )
    record = ContentRecord(**payload)
    assert record.do_now[0].why == "Starts the clock."
    assert record.never_do[0].consequence == "You may waive your right to more money."


# --- loader-level validation -------------------------------------------------


def test_authority_that_does_not_resolve_fails_load(tmp_path):
    _write_jsonl(
        tmp_path, "fire.jsonl", [_minimal_record(authority=[UNRESOLVABLE_CITATION])]
    )
    with pytest.raises(ContentLoadError) as exc_info:
        load_active_content(tmp_path)
    assert UNRESOLVABLE_CITATION in str(exc_info.value)


def test_authority_that_resolves_loads(tmp_path):
    _write_jsonl(tmp_path, "fire.jsonl", [_minimal_record()])
    active = load_active_content(tmp_path)
    assert len(active) == 1
    assert active[0].authority == [RESOLVABLE_CITATION]


def test_superseded_version_chain_only_newest_active(tmp_path):
    _write_jsonl(
        tmp_path,
        "fire.jsonl",
        [
            _minimal_record(version=1, superseded_by=2, title="Old title"),
            _minimal_record(version=2, superseded_by=None, title="New title"),
        ],
    )
    active = load_active_content(tmp_path)
    assert len(active) == 1
    assert active[0].version == 2
    assert active[0].title == "New title"


def test_dangling_superseded_by_fails(tmp_path):
    _write_jsonl(
        tmp_path,
        "fire.jsonl",
        [_minimal_record(version=1, superseded_by=99)],
    )
    with pytest.raises(ContentLoadError):
        load_active_content(tmp_path)


def test_duplicate_sequence_in_one_peril_fails(tmp_path):
    _write_jsonl(
        tmp_path,
        "fire.jsonl",
        [
            _minimal_record(phase_id="fire.p0.a", sequence=1, peril=["fire"]),
            _minimal_record(phase_id="fire.p0.b", sequence=1, peril=["fire"]),
        ],
    )
    with pytest.raises(ContentLoadError):
        load_active_content(tmp_path)


def test_duplicate_sequence_across_different_perils_ok(tmp_path):
    _write_jsonl(
        tmp_path,
        "fire.jsonl",
        [
            _minimal_record(phase_id="fire.p0.a", sequence=1, peril=["fire"]),
            _minimal_record(phase_id="water.p0.a", sequence=1, peril=["water"]),
        ],
    )
    active = load_active_content(tmp_path)
    assert len(active) == 2


def test_duplicate_version_in_same_chain_fails(tmp_path):
    _write_jsonl(
        tmp_path,
        "fire.jsonl",
        [
            _minimal_record(version=1, sequence=1),
            _minimal_record(version=1, sequence=2),
        ],
    )
    with pytest.raises(ContentLoadError):
        load_active_content(tmp_path)


def test_empty_data_dir_returns_empty_list(tmp_path):
    assert load_active_content(tmp_path) == []
