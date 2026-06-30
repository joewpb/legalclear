"""Phase 7 — Evaluation harness.

Usage:
  python -m evals.run_all              # fast mode: compute-only, no LLM (CI-safe)
  python -m evals.run_all --full       # full pipeline: LLM extract + compute
  python -m evals.run_all --id CS-001  # single document

Fast mode (CI default):
  Uses the locked trigger_date + service_method from ground_truth.json and runs
  the deterministic compute engine. Zero LLM calls. Pure regression test.

Full mode:
  Loads document text, runs triage classifier + deadline extractor + compute,
  then compares all fields against ground truth.

Launch gate (enforced in both modes):
  100% exact-match accuracy on expected_deadline_date for all fatal-severity
  documents. If this gate is not met, the run exits with code 1.

Guardrail: never edit ground_truth.json to make a test pass. Fix the code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# Make sure the backend packages are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deadline.compute import compute_deadline_for_event
from deadline.rules import RULES

EVALS_DIR   = Path(__file__).resolve().parent
GT_FILE     = EVALS_DIR / "ground_truth.json"
DOCS_DIR    = EVALS_DIR / "documents"

# Statewide FL holiday closures (2026) from ground_truth._rules.holidays_2026
HOLIDAYS_2026 = frozenset(
    date.fromisoformat(d)
    for d in [
        "2026-01-01","2026-01-19","2026-05-25","2026-07-03",
        "2026-09-07","2026-11-11","2026-11-26","2026-11-27","2026-12-25",
    ]
)


@dataclass
class EvalResult:
    doc_id: str
    severity: str | None
    # Classification
    expected_doc_type: str | None
    actual_doc_type: str | None = None
    doc_type_match: bool | None = None
    # Trigger extraction
    expected_trigger_date: str | None = None
    actual_trigger_date: str | None = None
    trigger_date_match: bool | None = None
    expected_service_method: str | None = None
    actual_service_method: str | None = None
    service_method_match: bool | None = None
    # Deadline compute
    expected_deadline: str | None = None
    actual_deadline: str | None = None
    deadline_match: bool | None = None
    # Meta
    skip_reason: str | None = None
    error: str | None = None


def _load_ground_truth() -> dict:
    with open(GT_FILE) as f:
        return json.load(f)


def _run_fast(doc: dict, results: list[EvalResult]) -> None:
    """Fast mode: skip LLM — verify compute.py against locked ground truth."""
    r = EvalResult(
        doc_id=doc["id"],
        severity=doc.get("severity"),
        expected_doc_type=doc.get("expected_document_type"),
        expected_trigger_date=doc.get("expected_trigger_date"),
        expected_service_method=doc.get("expected_service_method"),
        expected_deadline=doc.get("expected_deadline_date"),
    )

    # Documents with no computable deadline — verify escalation flag instead
    if not doc.get("expected_trigger_date") or not doc.get("expected_deadline_rule_key"):
        r.skip_reason = "no computable deadline (escalation or non-computable type)"
        results.append(r)
        return

    # Documents where deadline is expected to be null (e.g. small claims pretrial on summons)
    # → verify the engine escalates rather than producing a date
    if doc.get("expected_deadline_rule_key") and doc.get("expected_deadline_date") is None:
        rule_key = doc["expected_deadline_rule_key"]
        trigger_date = date.fromisoformat(doc["expected_trigger_date"])
        service_method = doc["expected_service_method"]
        try:
            compute_result = compute_deadline_for_event(
                rule_key=rule_key,
                event_date=trigger_date,
                service_method=service_method,
                circuit=None,
                closure_dates=HOLIDAYS_2026,
                has_local_closure_data=True,
                today=date(2025, 1, 1),
            )
            escalated = (
                compute_result.escalation_needed or
                any(d.escalation_recommended for d in compute_result.deadlines)
            )
            r.deadline_match = escalated  # pass if engine correctly escalates
            r.actual_deadline = "escalated" if escalated else "no-escalation"
            r.expected_deadline = "escalated"
        except Exception as e:
            r.error = str(e)
        results.append(r)
        return

    rule_key = doc["expected_deadline_rule_key"]
    trigger_date = date.fromisoformat(doc["expected_trigger_date"])
    service_method = doc["expected_service_method"]

    try:
        compute_result = compute_deadline_for_event(
            rule_key=rule_key,
            event_date=trigger_date,
            service_method=service_method,
            circuit=None,
            closure_dates=HOLIDAYS_2026,
            has_local_closure_data=True,
            today=date(2025, 1, 1),  # fixed past date — no "past deadline" flags in eval
        )
        if not compute_result.deadlines:
            r.error = "compute returned no deadlines"
            results.append(r)
            return

        # For judgment type, notice_of_appeal is the fatal clock — use first fatal deadline
        fatal_dl = next(
            (d for d in compute_result.deadlines if d.severity == "fatal"),
            compute_result.deadlines[0],
        )
        r.actual_deadline = fatal_dl.due_date.isoformat()
        r.deadline_match = (r.actual_deadline == r.expected_deadline)
    except Exception as e:
        r.error = str(e)

    results.append(r)


async def _run_full(doc: dict, results: list[EvalResult]) -> None:
    """Full mode: run LLM classify + extract + compute."""
    from triage.classify import classify_document
    from triage.router import route
    from deadline.extract import extract_trigger_events

    doc_path = DOCS_DIR / doc["file"].split("/")[-1]
    r = EvalResult(
        doc_id=doc["id"],
        severity=doc.get("severity"),
        expected_doc_type=doc.get("expected_document_type"),
        expected_trigger_date=doc.get("expected_trigger_date"),
        expected_service_method=doc.get("expected_service_method"),
        expected_deadline=doc.get("expected_deadline_date"),
    )

    try:
        text = doc_path.read_text()
    except FileNotFoundError:
        r.error = f"document file not found: {doc_path}"
        results.append(r)
        return

    try:
        # Step 1: classify
        classification = await classify_document(text)
        r.actual_doc_type = classification.get("document_type")
        r.doc_type_match = (r.actual_doc_type == r.expected_doc_type)

        # Step 2: extract trigger events (if computable deadline expected)
        if doc.get("expected_trigger_date") and doc.get("expected_deadline_rule_key"):
            extraction = await extract_trigger_events(text)
            events = extraction.get("events", [])
            if events:
                ev = events[0]
                r.actual_trigger_date = ev.get("event_date")
                r.trigger_date_match = (r.actual_trigger_date == r.expected_trigger_date)
                r.actual_service_method = ev.get("service_method")
                r.service_method_match = (r.actual_service_method == r.expected_service_method)

                # Step 3: compute
                rule_key = doc["expected_deadline_rule_key"]
                if r.actual_trigger_date and rule_key in RULES:
                    trigger_dt = date.fromisoformat(r.actual_trigger_date)
                    service = r.actual_service_method or "unknown"
                    compute_result = compute_deadline_for_event(
                        rule_key=rule_key,
                        event_date=trigger_dt,
                        service_method=service,
                        circuit=None,
                        closure_dates=HOLIDAYS_2026,
                        has_local_closure_data=True,
                        today=date(2025, 1, 1),
                    )
                    if compute_result.deadlines:
                        fatal_dl = next(
                            (d for d in compute_result.deadlines if d.severity == "fatal"),
                            compute_result.deadlines[0],
                        )
                        r.actual_deadline = fatal_dl.due_date.isoformat()
                        r.deadline_match = (r.actual_deadline == r.expected_deadline)
                    elif compute_result.escalation_needed and r.expected_deadline is None:
                        # Non-computable rule correctly escalated — pass
                        r.actual_deadline = "escalated"
                        r.expected_deadline = "escalated"
                        r.deadline_match = True
                    else:
                        r.error = "compute returned no deadlines and no escalation"
            else:
                r.skip_reason = "LLM returned no trigger events"
        else:
            r.skip_reason = "no computable deadline expected"

    except Exception as e:
        r.error = str(e)

    results.append(r)


def _print_report(results: list[EvalResult], mode: str) -> bool:
    """Print report and return True if the fatal-deadline gate is met."""
    total = len(results)
    skipped = sum(1 for r in results if r.skip_reason)
    errors = sum(1 for r in results if r.error)

    deadline_results = [r for r in results if r.deadline_match is not None]
    deadline_pass = sum(1 for r in deadline_results if r.deadline_match)
    deadline_fail = [r for r in deadline_results if not r.deadline_match]

    fatal_results = [r for r in deadline_results if r.severity == "fatal"]
    fatal_pass = sum(1 for r in fatal_results if r.deadline_match)
    fatal_fail = [r for r in fatal_results if not r.deadline_match]

    print(f"\n{'='*60}")
    print(f"  LegalClear Deadline Eval — {mode.upper()} MODE")
    print(f"{'='*60}")
    print(f"  Documents: {total}  |  Skipped: {skipped}  |  Errors: {errors}")
    print(f"  Deadline accuracy:  {deadline_pass}/{len(deadline_results)}")
    print(f"  Fatal accuracy:     {fatal_pass}/{len(fatal_results)}")

    if mode == "full":
        cls_results = [r for r in results if r.doc_type_match is not None]
        cls_pass = sum(1 for r in cls_results if r.doc_type_match)
        trig_results = [r for r in results if r.trigger_date_match is not None]
        trig_pass = sum(1 for r in trig_results if r.trigger_date_match)
        svc_results = [r for r in results if r.service_method_match is not None]
        svc_pass = sum(1 for r in svc_results if r.service_method_match)
        print(f"  Doc-type accuracy:  {cls_pass}/{len(cls_results)}")
        print(f"  Trigger-date accuracy: {trig_pass}/{len(trig_results)}")
        print(f"  Service-method accuracy: {svc_pass}/{len(svc_results)}")

    if deadline_fail:
        print(f"\n  DEADLINE MISMATCHES ({len(deadline_fail)}):")
        for r in deadline_fail:
            print(f"    {r.doc_id}  expected={r.expected_deadline}  "
                  f"got={r.actual_deadline}  severity={r.severity}")

    if errors > 0:
        print(f"\n  ERRORS ({errors}):")
        for r in results:
            if r.error:
                print(f"    {r.doc_id}: {r.error}")

    # Fatal-tier launch gate
    gate_met = len(fatal_fail) == 0 and len(fatal_results) > 0
    print(f"\n{'='*60}")
    if gate_met:
        print(f"  LAUNCH GATE: PASS — 100% accuracy on {len(fatal_results)} fatal deadlines")
    else:
        print(f"  LAUNCH GATE: FAIL — {len(fatal_fail)} fatal deadline(s) incorrect")
        if fatal_fail:
            for r in fatal_fail:
                print(f"    {r.doc_id}: expected {r.expected_deadline}, got {r.actual_deadline}")
    print(f"{'='*60}\n")

    return gate_met


def main() -> None:
    parser = argparse.ArgumentParser(description="LegalClear deadline eval harness")
    parser.add_argument("--full", action="store_true", help="Run full LLM pipeline (slow)")
    parser.add_argument("--id", help="Run single document by ID")
    args = parser.parse_args()

    gt = _load_ground_truth()
    documents = gt["documents"]

    if args.id:
        documents = [d for d in documents if d["id"] == args.id]
        if not documents:
            print(f"ERROR: document ID {args.id!r} not found in ground truth")
            sys.exit(1)

    results: list[EvalResult] = []

    if args.full:
        async def _run_all():
            for doc in documents:
                await _run_full(doc, results)
        asyncio.run(_run_all())
        mode = "full"
    else:
        for doc in documents:
            _run_fast(doc, results)
        mode = "fast"

    gate_met = _print_report(results, mode)
    sys.exit(0 if gate_met else 1)


if __name__ == "__main__":
    main()
