"""verify_slist gate — test-the-tester locks (Decision 21).

The gate is a checker; per the standing rule a checker must prove it can
catch what it claims to catch. These tests build real throwaway git repos
in tmp_path and assert the flag behavior end-to-end, plus pure-function
coverage of the parser core.
Run: cd backend && uv run python -m pytest tests/test_verify_slist.py -v
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))


from verify_slist import (
    bad_headings,
    extract_fixes,
    git_log_subjects,
    parse_entries,
    scan,
)

FOLLOW_UPS_FIXTURE = """# FOLLOW_UPS

## S9-1 — OPEN a real open work item
Body text.

## S9-2 — RESOLVED was open, fix landed and list was back-annotated
Body text.

## S9-3 — OPEN (deliberate) known-open with a reason, fix not landed
Body text.

## S9-4 — RECORDED a diagnosis record, not a work item
Body text.
"""


def _repo(tmp_path: Path, commits: list[str]) -> Path:
    """Create a git repo with FOLLOW_UPS.md and the given commit subjects."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "FOLLOW_UPS.md").write_text(FOLLOW_UPS_FIXTURE)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "tester"], cwd=root, check=True
    )
    subprocess.run(["git", "add", "FOLLOW_UPS.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "docs: seed entries"], cwd=root, check=True)
    for subject in commits:
        (root / "stamp.txt").write_text(subject)
        subprocess.run(["git", "add", "stamp.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", subject], cwd=root, check=True)
    return root


# ── pure core ──────────────────────────────────────────────────────────────

def test_parse_entries_states_and_deliberate():
    entries = parse_entries(FOLLOW_UPS_FIXTURE)
    e1 = entries["S9-1"]
    assert (e1.id, e1.state, e1.deliberate) == ("S9-1", "OPEN", False)
    assert e1.lineno == 3
    assert entries["S9-2"].state == "RESOLVED"
    assert entries["S9-3"].state == "OPEN" and entries["S9-3"].deliberate
    assert entries["S9-4"].state == "RECORDED"


def test_bad_headings_detects_grammar_violations():
    text = FOLLOW_UPS_FIXTURE + "\n## no id here just words\n"
    bad = bad_headings(text)
    assert any("no id here" in h for _, h in bad)


def test_extract_fixes_matches_commit_subjects():
    assert extract_fixes("feat: fixes S2-7 never substitute issuance") == {"S2-7"}
    assert extract_fixes("fix(b1-s2-7): deadline rules declare anchors") == set()
    assert extract_fixes("docs: fix the typo, no id") == set()


def test_git_log_subjects_roundtrip(tmp_path):
    root = _repo(tmp_path, ["feat: fixes S9-1 the thing"])
    subjects = git_log_subjects(root)
    assert any("fixes S9-1" in s for s in subjects)


# ── end-to-end gate (self-validation) ─────────────────────────────────────

def test_clean_repo_no_flags(tmp_path):
    root = _repo(tmp_path, [])
    flags, _warnings = scan(root)
    assert flags == [] and _warnings == []


def test_open_entry_with_fixes_commit_is_flagged(tmp_path):
    root = _repo(tmp_path, ["feat: fixes S9-1 service-date anchor"])
    flags, _warnings = scan(root)
    assert len(flags) == 1
    assert "S9-1 is OPEN" in flags[0] and "fixes S9-1" in flags[0]


def test_resolved_entry_with_fixes_commit_is_clean(tmp_path):
    root = _repo(tmp_path, ["feat: fixes S9-2 service-date anchor"])
    flags, _warnings = scan(root)
    assert flags == []


def test_deliberate_open_entry_with_fixes_commit_is_clean(tmp_path):
    root = _repo(tmp_path, ["feat: fixes S9-3 service-date anchor"])
    flags, _warnings = scan(root)
    assert flags == []


def test_fixes_for_unknown_id_is_warning_not_flag(tmp_path):
    root = _repo(tmp_path, ["feat: fixes S9-99 nonexistent entry"])
    flags, warnings = scan(root)
    assert flags == []
    assert len(warnings) == 1 and "S9-99" in warnings[0]


def test_missing_follow_ups_file_is_flagged(tmp_path):
    root = tmp_path / "emptyrepo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    flags, _warnings = scan(root)
    assert len(flags) == 1 and "missing" in flags[0]


def test_grammar_violation_is_flagged(tmp_path):
    root = _repo(tmp_path, [])
    (root / "FOLLOW_UPS.md").write_text(
        "## entry without the grammar\nbody\n"
    )
    subprocess.run(["git", "add", "FOLLOW_UPS.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "docs: bad heading"], cwd=root, check=True)
    flags, _warnings = scan(root)
    assert len(flags) == 1 and "grammar" in flags[0]
