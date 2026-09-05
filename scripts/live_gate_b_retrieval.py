# Live gate for the Phase B retrieval hardening (2026-08-30 plan).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the NOINDEX mock PDF to a RUNNING backend on :8002 and asserts,
deterministically (LLM variance never fails this gate):

  1. a relevant_opinions event arrives and is non-empty
  2. EVERY returned opinion has a non-empty citation (kills the Tracey
     class — a case the UI cannot point to must never surface)
  3. every returned opinion matches >=1 derived fact term, OR >=2
     substantive tag terms (the two-tier admission fallback)
  4. homicide exclusion holds (report has no homicide charge -> no
     homicide rows in the output)
  5. local derive == server situation_tags_used (same code, same JSON)

Case names + matched-term counts are printed for Joe's eyeball (Nieminski
presence is informational — LLM text variance is not a regression).

Usage (backend must already be running on :8002 with backend/.env sourced):
    uv run --project backend python scripts/live_gate_b_retrieval.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera_NOINDEX.pdf
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

ENDPOINT = os.environ.get(
    "LC_B_GATE_ENDPOINT",
    "http://127.0.0.1:8002/api/police-report/analyze",
)


def _load_env() -> None:
    """Load backend/.env without overriding already-set shell env."""
    env = BACKEND_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: live_gate_b_retrieval.py <path-to-noindex-pdf>",
              file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"ERROR: file not found: {sys.argv[1]}", file=sys.stderr)
        return 2

    _load_env()
    from src.core.json_utils import strip_markdown_fences
    from src.services.opinion_retrieval import (
        _derive_fact_terms,
        _report_has_homicide_charge,
        _row_is_homicide,
        _substantive_search_terms,
        derive_situation_tags,
    )

    print(f"POST {ENDPOINT}  [{p.name}, {p.stat().st_size} bytes]")
    with open(p, "rb") as fh:
        resp = requests.post(
            ENDPOINT,
            files={"file": (p.name, fh, "application/pdf")},
            data={"language": "en"},
            stream=True,
            timeout=(30, 300),
        )
    resp.raise_for_status()

    # Tolerant parser: works with BOTH stream protocols (Phase A typed
    # frames, or the legacy data-only fragment stream).
    raw_chunks: list[str] = []
    opinions_event: dict | None = None
    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            raw_chunks.append(payload)
            continue
        etype = obj.get("type") if isinstance(obj, dict) else None
        if etype == "relevant_opinions":
            opinions_event = obj
        elif etype in ("risk_analysis", "case_context", "progress",
                       "error") or (isinstance(obj, dict)
                                    and obj.get("error")):
            pass
        else:
            raw_chunks.append(payload)

    full_text = "".join(raw_chunks)
    parsed = None
    try:
        parsed = json.loads(strip_markdown_fences(full_text))
    except json.JSONDecodeError:
        pass

    checks: list[tuple[str, bool, str]] = []

    if parsed is None:
        checks.append(("analysis JSON parsed from stream", False, "no JSON"))
    else:
        checks.append(("analysis JSON parsed from stream", True, "ok"))

    if opinions_event is None:
        checks.append(("relevant_opinions event received", False, "missing"))
        checks.append(("non-empty opinions", False, "n/a"))
        checks.append(("citations all present", False, "n/a"))
        checks.append(("two-tier admission", False, "n/a"))
        checks.append(("homicide exclusion", False, "n/a"))
        checks.append(("local==server tags", False, "n/a"))
    else:
        opinions = opinions_event.get("opinions") or []
        checks.append(("relevant_opinions event received", True, "ok"))
        checks.append((
            "non-empty opinions",
            bool(opinions),
            f"{len(opinions)} opinion(s)",
        ))
        _PLACEHOLDERS = {"n/a", "na", "null", "none", "unknown", "tbd",
                         "pending", "not cited"}

        def _real_citation(o: dict) -> bool:
            c = o.get("citation")
            return (
                isinstance(c, str) and bool(c.strip())
                and c.strip().casefold() not in _PLACEHOLDERS
            )

        checks.append((
            "every opinion has a verifiable citation",
            all(_real_citation(o) for o in opinions),
            repr([o.get("case_name") for o in opinions
                  if not _real_citation(o)]),
        ))

        fact_terms = _derive_fact_terms(parsed) if parsed else []
        tags = derive_situation_tags(parsed) if parsed else []
        substantive = _substantive_search_terms(set(tags), fact_terms)
        fact_set = {t.casefold() for t in fact_terms}
        tag_only = {t for t in substantive if t not in fact_set}

        def _count(text: str | None, terms) -> int:
            if not text:
                return 0
            low = text.casefold()
            return sum(1 for t in terms if t in low)

        bad = []
        for o in opinions:
            fm = _count(o.get("summary_plain"), fact_set)
            tm = _count(o.get("summary_plain"), tag_only)
            if not (fm >= 1 or tm >= 2):
                bad.append((o.get("case_name"), fm, tm))
        checks.append((
            "two-tier admission (>=1 fact term, else >=2 tag terms)",
            not bad,
            repr(bad),
        ))

        report_homicide = _report_has_homicide_charge(parsed)
        homicide_names = [
            o.get("case_name") for o in opinions if _row_is_homicide(o)
        ]
        checks.append((
            "homicide exclusion (no homicide charge in report)",
            report_homicide or not homicide_names,
            f"report_homicide={report_homicide} rows={homicide_names!r}",
        ))

        server_tags = opinions_event.get("situation_tags_used")
        checks.append((
            "local derive == server situation_tags_used",
            server_tags == tags,
            f"local={tags!r} server={server_tags!r}",
        ))

        print(f"\nfact terms ({len(fact_terms)}): {fact_terms!r}")
        print(f"situation_tags_used: {server_tags!r}\n")
        print("returned opinions:")
        for i, o in enumerate(opinions):
            fm = _count(o.get("summary_plain"), fact_set)
            tm = _count(o.get("summary_plain"), tag_only)
            print(
                f"  [{i}] {o.get('case_name')}  fact_matched={fm} "
                f"tag_matched={tm}  cite_count={o.get('cite_count')}  "
                f"citation={o.get('citation')}",
            )

    print("\nGATE VERDICT")
    ok = True
    for name, passed, detail in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
