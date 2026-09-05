# Live gate for the police-report case-law relevance fix (2026-08).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the LC-TEST-001 mock PDF (Miranda / language-access / 4A-consent /
Terry-stop defects) to a RUNNING backend on :8001 and prints the
situation_tags_used and the returned opinions — the before/after evidence
for the relevance fix. Also derives the fact terms locally (same
deterministic function, same repo) so the report shows exactly which facts
reached the retrieval query.

Usage (backend must already be running on :8001 with backend/.env sourced):
    uv run --project backend python scripts/lc_police_repro.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera.pdf

PASS criteria: top opinions are 4A/consent/Miranda-language cases
(Jardines / Bustamonte class) — ZERO murder/death-penalty/famous-generic
cases; situation_tags_used unchanged from
['fifth_amendment','fourth_amendment','language_access','misdemeanor',
'probable_cause','sixth_amendment','unlawful_search'].
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

ENDPOINT = os.environ.get("LC_REPRO_ENDPOINT", "http://127.0.0.1:8001/api/police-report/analyze")


def _load_env() -> None:
    """Load backend/.env without overriding already-set shell env (matches
    the scripts/ convention). Needed only for the local fact-term derivation
    imports, not for the HTTP call."""
    env = BACKEND_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _bar(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main(pdf_path: str) -> int:
    p = Path(pdf_path)
    if not p.is_file():
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        return 2

    _load_env()
    from src.core.json_utils import strip_markdown_fences  # noqa: E402
    from src.services.opinion_retrieval import (  # noqa: E402
        _derive_fact_terms,
        derive_situation_tags,
    )

    _bar(f"POST {ENDPOINT}  [{p.name}, {p.stat().st_size} bytes]")
    with open(p, "rb") as fh:
        files = {"file": (p.name, fh, "application/pdf")}
        resp = requests.post(
            ENDPOINT, files=files, data={"language": "en"},
            stream=True, timeout=(30, 300),
        )
    resp.raise_for_status()

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
        elif etype in ("risk_analysis", "case_context") or isinstance(obj, dict) and obj.get("error"):
            pass
        else:
            # Fragment of the analysis JSON (has no "type" key).
            raw_chunks.append(payload)

    full_text = "".join(raw_chunks)
    parsed = None
    try:
        parsed = json.loads(strip_markdown_fences(full_text))
    except json.JSONDecodeError:
        pass

    if parsed:
        _bar("LOCAL DERIVATION (same deterministic functions as the server)")
        tags = derive_situation_tags(parsed)
        print(f"derive_situation_tags  = {tags!r}")
        fact_terms = _derive_fact_terms(parsed)
        print(f"fact terms ({len(fact_terms)}): {fact_terms!r}")
    else:
        _bar("WARNING: analysis JSON did not parse from the stream")

    if opinions_event is None:
        _bar("NO relevant_opinions EVENT RECEIVED")
        return 1

    _bar("SERVER EVENT — relevant_opinions")
    print(f"situation_tags_used = {opinions_event.get('situation_tags_used')!r}")
    opinions = opinions_event.get("opinions") or []
    print(f"opinions returned   = {len(opinions)}")
    for i, op in enumerate(opinions):
        print(f"  [{i}] {op.get('case_name')}  | cite_count={op.get('cite_count')}  "
              f"| {op.get('citation')}  | {op.get('court')}")
        summary = (op.get("summary_plain") or "").replace("\n", " ")
        if summary:
            print(f"       summary: {summary[:200]}")

    verdict = _gate_verdict(parsed, opinions, opinions_event)
    _bar("GATE VERDICT")
    for ok, line in verdict:
        print(f"  {'PASS' if ok else 'FAIL'}  {line}")
    if not all(ok for ok, _ in verdict):
        return 1

    if os.environ.get("LC_DEEP") and parsed is not None:
        _run_deep_diagnostic(parsed, tags)

    _bar("DONE")
    return 0


# ── Gate criteria (Joe ruling 2026-08-27) ───────────────────────────────────
# The gate asserts only what is deterministic. LLM output variance is NOT a
# code regression and must not fail the gate; the mapper's determinism is.
_REFERENCE_SUBSTANTIVE_TAGS = frozenset({
    # Aug-24 reference run minus charge-class tags (misdemeanor/felony/dui/
    # traffic_stop) — the substantive set the fix must preserve.
    "fifth_amendment", "fourth_amendment", "language_access",
    "probable_cause", "sixth_amendment", "unlawful_search",
})
_CHARGE_CLASS_TAGS_FOR_GATE = frozenset({
    "misdemeanor", "felony", "dui", "drug_trafficking", "traffic_stop",
})
# sha256 of inspect.getsource(derive_situation_tags) at review time
# (2026-08-27, mapper byte-identical to HEAD). Recompute ONLY after a
# deliberate, reviewed mapper change; a drift here means the mapper changed
# outside review.
_MAPPER_REF_HASH = "e46edd5a2cf8ea912dc2202224e4dcdfbee652407333900232a29990f9b3d520"


def _gate_verdict(parsed, opinions, opinions_event) -> list[tuple[bool, str]]:
    """Deterministic Phase 3 gate checks. Returns (ok, line) pairs."""
    import hashlib
    import inspect

    from src.services.opinion_retrieval import (  # noqa: F401
        _report_has_homicide_charge,
        _row_is_homicide,
        derive_situation_tags as _ds,
    )

    checks: list[tuple[bool, str]] = []

    # 1. Mapper-identical: hash the reviewed mapper source against the pin.
    src = inspect.getsource(_ds)
    h = hashlib.sha256(src.encode()).hexdigest()
    checks.append((
        h == _MAPPER_REF_HASH,
        f"mapper source hash {h[:16]}… {'==' if h == _MAPPER_REF_HASH else '!='} "
        f"reference {_MAPPER_REF_HASH[:16]}…",
    ))

    # 2. Live consistency: the server's derive must equal the local derive on
    # the SAME analysis JSON (catches the server running stale/different code).
    if parsed:
        local_tags = _ds(parsed)
        server_tags = opinions_event.get("situation_tags_used")
        checks.append((
            local_tags == server_tags,
            f"local derive {local_tags!r} == server {server_tags!r}",
        ))
    else:
        checks.append((False, "analysis JSON did not parse — cannot compare tags"))

    # 3. Substantive-tag-set subset: the reference run's substantive tags
    # must all be present in the current run's substantive tags. Charge-class
    # tags are excluded from both sides — LLM charge-text variance is not a
    # code regression.
    if parsed:
        current = {t for t in _ds(parsed)} - _CHARGE_CLASS_TAGS_FOR_GATE
        checks.append((
            _REFERENCE_SUBSTANTIVE_TAGS <= current,
            f"reference substantive {sorted(_REFERENCE_SUBSTANTIVE_TAGS)!r} "
            f"⊆ current {sorted(current)!r}",
        ))
    else:
        checks.append((False, "analysis JSON did not parse — no tag-set check"))

    # 4. Homicide exclusion on the OUTPUT: no returned opinion may be a
    # homicide case when the report carries no homicide charge.
    report_homicide = _report_has_homicide_charge(parsed)
    homicide_names = [
        op.get("case_name")
        for op in opinions
        if _row_is_homicide(op)
    ]
    checks.append((
        report_homicide or not homicide_names,
        f"homicide rows in output {homicide_names!r} (report has homicide "
        f"charge: {report_homicide})",
    ))

    # 5. Non-empty result — an empty opinion list is a silent failure.
    checks.append((bool(opinions), f"{len(opinions)} opinion(s) returned"))

    return checks


def _run_deep_diagnostic(parsed: dict, tags: list[str]) -> None:
    """Direct-DB look at both retrieval paths (same queries the service
    runs) so a failing gate run shows WHY. Diagnostic-only."""
    from src.services.opinion_retrieval import (  # noqa: F401
        _build_ilike_filter,
        _count_matched_terms,
        _derive_fact_terms,
        _OPINION_COLUMNS,
        _pool_anchor_terms,
        _substantive_search_terms,
        db as _db,
    )

    if _db.client is None:
        print("DEEP: no Supabase client (env missing)")
        return
    fact_terms = _derive_fact_terms(parsed)
    substantive = _substantive_search_terms(set(tags), fact_terms)

    def fmt(row, extra=""):
        m = _count_matched_terms(row.get("summary_plain"), substantive)
        return (f"    {row.get('case_name')!r:45.45} matched={m} "
                f"cite={row.get('cite_count')} {extra}")

    _bar(f"DEEP — tag-overlap rows (tags={sorted(set(tags))!r})")
    tag_result = (
        _db.client.table("legal_opinions")
        .select(_OPINION_COLUMNS + ", situation_tags")
        .overlaps("situation_tags", tags)
        .eq("quality_flagged", False)
        .limit(500)
        .execute()
    )
    tag_rows = []
    for row in tag_result.data or []:
        op_tags = set(row.get("situation_tags") or [])
        overlap = len(op_tags & set(tags))
        m = _count_matched_terms(row.get("summary_plain"), substantive)
        tag_rows.append((m, overlap, row))
    tag_rows.sort(key=lambda t: (t[0], t[1], t[2].get("cite_count") or 0),
                  reverse=True)
    for m, ov, row in tag_rows[:12]:
        print(fmt(row, f"overlap={ov}"))

    _bar("DEEP — ILIKE pool (single-anchor, no order, limit 200)")
    anchors = _pool_anchor_terms(fact_terms)
    print(f"    anchor candidates: {anchors!r}")
    ilike_result = None
    for anchor in anchors:
        try:
            ilike_result = (
                _db.client.table("legal_opinions")
                .select(_OPINION_COLUMNS)
                .or_(_build_ilike_filter([anchor]))
                .eq("quality_flagged", False)
                .limit(200)
                .execute()
            )
            print(f"    anchor {anchor!r}: OK")
            break
        except Exception as e:
            print(f"    anchor {anchor!r}: FAIL {str(e)[:70]}")
    pool = []
    for row in (ilike_result.data if ilike_result else []) or []:
        m = _count_matched_terms(row.get("summary_plain"), substantive)
        pool.append((m, row))
    pool.sort(key=lambda t: (t[0], t[1].get("cite_count") or 0), reverse=True)
    print(f"    pool size = {len(pool)}")
    for m, row in pool[:12]:
        print(fmt(row))

    _bar("DEEP — merged top-6 (fact-mode ranking: matched, overlap, cite)")
    merged = [(m, 0, row) for m, row in pool] + [
        (m, ov, row) for m, ov, row in tag_rows
    ]
    merged.sort(key=lambda t: (t[0], t[1], t[2].get("cite_count") or 0),
                reverse=True)
    for m, ov, row in merged[:6]:
        print(fmt(row, f"overlap={ov}"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "usage: uv run --project backend python scripts/lc_police_repro.py <path-to-pdf>",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
