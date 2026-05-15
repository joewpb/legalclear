"""Phase 19 verification — copied verbatim from
phases/source/PHASE_19_forms_finder.md.

Static-data check: no backend required.
"""
import json
import os


# Resolve repo root robustly so the test works whether invoked from repo
# root or from backend/.
def _index_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(
        os.path.join(here, "..", "..", "frontend", "src", "data", "fl_courts_forms_index.json")
    )


def test_forms_index_exists():
    with open(_index_path()) as f:
        data = json.load(f)
    assert len(data) >= 18, f"Need ≥18 entries, got {len(data)}"


def test_all_case_types_covered():
    with open(_index_path()) as f:
        data = json.load(f)
    case_types = {entry["case_type"] for entry in data}
    required = {"Family", "Civil", "Probate", "Small Claims", "Traffic", "Criminal"}
    assert required.issubset(case_types), f"Missing case types: {required - case_types}"


def test_coverage_per_case_type():
    with open(_index_path()) as f:
        data = json.load(f)
    counts = {"Family": 0, "Civil": 0, "Probate": 0, "Small Claims": 0, "Traffic": 0, "Criminal": 0}
    for entry in data:
        counts[entry["case_type"]] += 1
    assert counts["Family"] >= 5
    assert counts["Civil"] >= 3
    assert counts["Probate"] >= 3
    assert counts["Small Claims"] >= 3
    assert counts["Traffic"] >= 2
    assert counts["Criminal"] >= 2


def test_urls_not_fabricated():
    with open(_index_path()) as f:
        data = json.load(f)
    allowed_domains = ["flcourts.gov", "fdle.state.fl.us", "flhsmv.gov", "flclerks.com"]
    for entry in data:
        for form in entry["forms"]:
            assert any(d in form["url"] for d in allowed_domains), \
                f"Suspect URL (not on approved govt domain): {form['url']}"


if __name__ == "__main__":
    test_forms_index_exists()
    test_all_case_types_covered()
    test_coverage_per_case_type()
    test_urls_not_fabricated()
    print("PHASE 19 COMPLETE — all checks passed.")
