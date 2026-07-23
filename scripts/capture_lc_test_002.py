# Manual diagnostic script — requires a valid ANTHROPIC_API_KEY (and an
# ANTHROPIC_BASE_URL override when .env points at a gateway); NOT run in CI or
# the test suite. Run by hand only.
"""One-off ground-truth capture for LC-TEST-002 (Whitfield / Port St. Lucie
disorderly-conduct summons).

Runs the PDF through PoliceReportAnalyzerV2 exactly as the live endpoint does
(same SYSTEM_PROMPT, same model claude-sonnet-4-6, same PDF text-extraction +
content construction), then prints:

  1. Full raw V2 result JSON (charges_explained + discrepancies w/ defect_category)
  2. derive_situation_tags() output (the exact tags=[...] list)
  3. get_relevant_opinions() result for those tags

Usage (run from the repo root; env is loaded from backend/.env automatically):
    ANTHROPIC_BASE_URL=https://api.anthropic.com \\
        uv run --project backend python scripts/capture_lc_test_002.py /path/to/LC-TEST-002.pdf

Note on faithfulness: the live endpoint (/api/police-report/analyze) calls
analyze_stream(); this script calls analyze(), the non-streaming twin. Both
issue the identical Claude request (same system prompt, same user content,
same model) and both parse the same JSON via _strip_fences. The
discrepancies[].defect_category and charges_explained[].charge values are
produced by that one Claude call, so they are identical between the two
methods. We use analyze() only because it returns the parsed dict directly
instead of forcing us to reassemble SSE chunks.

Diagnostic-only. Mutates nothing.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def _load_env() -> None:
    """Load backend/.env without overriding already-set shell env (matches the
    scripts/ convention, e.g. ingest_forms.py). Lets an ANTHROPIC_BASE_URL
    passed on the command line win over the .env gateway value."""
    env = BACKEND_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_env()

from src.agents.police_report_v2 import PoliceReportAnalyzerV2  # noqa: E402
from src.services.opinion_retrieval import (  # noqa: E402
    derive_situation_tags,
    get_relevant_opinions,
)


def _bar(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


async def main(pdf_path: str) -> int:
    p = Path(pdf_path)
    if not p.is_file():
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        return 2

    file_bytes = p.read_bytes()
    filename = p.name

    _bar(f"STAGE 1 — PoliceReportAnalyzerV2.analyze({filename})  [{len(file_bytes)} bytes]")
    analyzer = PoliceReportAnalyzerV2()
    result = await analyzer.analyze(file_bytes, filename=filename, language="en")

    if not isinstance(result, dict) or result.get("error"):
        _bar("V2 RESULT — ERROR / NON-JSON")
        print(json.dumps(result, indent=2))
        return 1

    # ---- 1. Full raw V2 JSON, with the two fields of interest highlighted ----
    _bar("STAGE 2 — RAW V2 RESULT (full JSON)")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    _bar("STAGE 2a — charges_explained[]  (charge text — answers Q(a): was 'misdemeanor' literal?)")
    for i, c in enumerate(result.get("charges_explained", [])):
        print(f"  [{i}] charge       = {c.get('charge')!r}")
        print(f"      plain_english = {c.get('plain_english')!r}")
    blob = " ".join(
        f"{c.get('charge', '')} {c.get('plain_english', '')}"
        for c in result.get("charges_explained", []) or []
    )
    print(f"  -> literal 'misdemeanor' present in charge blob: {'misdemeanor' in blob.lower()}")

    _bar("STAGE 2b — discrepancies[]  (answers Q(b): defect_category per gap)")
    for i, d in enumerate(result.get("discrepancies", [])):
        print(f"  [{i}] severity        = {d.get('severity')!r}")
        print(f"      defect_category = {d.get('defect_category')!r}")
        print(f"      description      = {d.get('description')!r}")

    # ---- 3. derive_situation_tags ----
    _bar("STAGE 3 — derive_situation_tags(result)  (the exact tags=[...] list)")
    tags = derive_situation_tags(result)
    print(f"tags = {tags!r}")
    print(f"miranda_noted            = {result.get('miranda_noted')!r}")
    print(f"probable_cause_present   = {result.get('probable_cause_present')!r}")

    # ---- 4. get_relevant_opinions ----
    _bar("STAGE 4 — get_relevant_opinions(tags)")
    opinions = get_relevant_opinions(tags)
    print(f"({len(opinions)} opinion(s) returned)")
    for i, op in enumerate(opinions):
        print(f"  [{i}] {op.get('case_name')}  | cite_count={op.get('cite_count')}  "
              f"| {op.get('citation')}")
        summary = (op.get("summary_plain") or "").replace("\n", " ")
        if summary:
            print(f"       summary: {summary[:160]}")

    _bar("DONE")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: uv run --project backend python scripts/capture_lc_test_002.py <path-to-pdf>",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
