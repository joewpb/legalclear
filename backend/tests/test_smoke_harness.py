"""Test-the-tester: the smoke harness itself must fail loudly.

FOLLOW_UPS silent-check instance #5 closure (2026-08-27): a check that can
pass silently is not a check — including the harness that enforces that rule.
The smoke harness printed "ALL PASS" twice while live steps were FAIL
(instance #4: expect=None; instance #5: the tally keyed on the evidence
string instead of the ok flag). This test runs the harness's built-in
KNOWN-FAIL scenario (`--selftest`, stub transport, no network) and asserts
the harness reports the known failure as FAIL and exits 0 only when it does.
If the harness ever regresses to silently passing a failure, this test fails.

Pure subprocess test — no LLM, no Supabase, no network.
"""

import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(REPO, "scripts", "smoke_pc_claims.py")


def test_smoke_harness_selftest_reports_fail():
    """Known-fail scenario must be reported FAIL, loudly, with the right tally."""
    r = subprocess.run(
        [sys.executable, SCRIPT, "--selftest"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = r.stdout + r.stderr
    assert r.returncode == 0, (
        f"selftest exited {r.returncode} — the harness can pass silently:\n{out}"
    )
    assert "SELFTEST PASS" in out, f"selftest did not report PASS:\n{out}"
    assert "known-fail" in out, f"selftest output missing the known-fail step:\n{out}"
