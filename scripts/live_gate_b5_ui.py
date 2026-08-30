#!/usr/bin/env python3
"""B5 UI live gate — two legs against prod (S2-7 UI half, scope 2026-08-30).

Leg A (escalation leg): upload a summons fixture whose only date is an
issuance line ("DATED this 14th day of August, 2026") → analyze → the anchor
gate MUST escalate (escalation_needed, reasons naming 'served' + § 83.60(2)),
zero deadline rows. This is the ask-the-user half firing.

Leg B (supply leg): PUT service-date 2026-08-17 / personal → exactly ONE
deadline, due 2026-08-24 — computed INDEPENDENTLY here (5 business days from
Aug 17, Mon, skipping the weekend), never by trusting the engine — trace
cites § 83.60(2), and document_service_facts holds exactly one row with
provenance 'user_supplied' (B5-f3 single-row invariant).

S3-5E discipline: every call declares a status expectation AND a content
validator; no expect=None. Any failed assertion aborts with evidence printed.

Runs against the live Railway backend; creds read from backend/.env
(API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY) — values never printed.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / "backend" / ".env"

PROD = "https://zesty-delight-production-b533.up.railway.app"

FIXTURE = (
    "IN THE COUNTY COURT IN AND FOR SAINT LUCIE COUNTY, FLORIDA\n"
    "CASE NO. 2026-CC-004242\n\n"
    "SUMMONS — EVICTION / RESIDENTIAL\n\n"
    "TO: TEST TENANT\n"
    "2000 GATEWAY AVE\n"
    "PORT SAINT LUCIE, FL 34953\n\n"
    "A lawsuit has been filed against you. You are required to serve a "
    "written response to the attached complaint within the time allowed by "
    "law. Failure to respond may result in a default judgment being entered "
    "against you for the relief demanded in the complaint.\n\n"
    "DATED this 14th day of August, 2026.\n\n"
    "CLERK OF THE COUNTY COURT\n"
)

FIXTURE_PATH = ROOT / "scripts" / "fixtures" / "b5_ui_summons.pdf"
# Regenerate: cd backend && uv run python ../scripts/gen_b5_ui_fixture.py

# Independent calendar math — the gate's expectation, not the engine's output.
def _add_business_days(start: date, n: int) -> date:
    d, added = start, 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            added += 1
    return d


def _env() -> dict[str, str]:
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class GateFail(Exception):
    pass


def call(method: str, url: str, *, expect_status: int, validate, headers=None,
         body=None) -> dict:
    """One HTTP call with a declared status expectation + content validator."""
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.status
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode()
    if status != expect_status:
        raise GateFail(f"{method} {url} -> status {status} (expected {expect_status}); body: {raw[:300]}")
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise GateFail(f"{method} {url} -> non-JSON body: {raw[:300]}")
    problem = validate(data)
    if problem:
        raise GateFail(f"{method} {url} -> {problem}; evidence: {json.dumps(data)[:400]}")
    return data


def main() -> int:
    env = _env()
    api_key = env.get("API_KEY", "")
    sb_url = env.get("SUPABASE_URL", "")
    sb_key = env.get("SUPABASE_SERVICE_KEY", "")
    if not (api_key and sb_url and sb_key):
        print("GATE ABORT: backend/.env missing API_KEY/SUPABASE_URL/SUPABASE_SERVICE_KEY")
        return 2

    evidence: list[str] = []
    ok = lambda msg: evidence.append(f"  PASS {msg}")

    # ── Leg A: upload fixture → analyze → escalation, zero rows ────────────
    upload_headers = {
        "x-api-key": api_key,
        "user-id": "b5-ui-live-gate",
        "filename": "b5_ui_live_gate_fixture.pdf",
        "email": "gate@legalclear.test",
        "lang": "en",
    }
    if not FIXTURE_PATH.exists():
        raise GateFail(f"fixture missing: {FIXTURE_PATH} — run gen_b5_ui_fixture.py")
    up = call("POST", f"{PROD}/upload", expect_status=200,
              headers=upload_headers, body=FIXTURE_PATH.read_bytes(),
              validate=lambda d: "missing document_id" if not d.get("document_id")
              else ("missing session_id" if not d.get("session_id") else None))
    ok(f"upload -> document_id + session_id returned (status 200)")
    doc_id, session_id = up["document_id"], up["session_id"]

    analyze = call(
        "POST", f"{PROD}/api/deadline/analyze/{doc_id}",
        expect_status=200, headers={"x-api-key": api_key},
        validate=lambda d: "escalation_needed is not True" if not d.get("escalation_needed") else None,
    )
    reasons = analyze.get("escalation_reasons") or []
    joined = " ".join(reasons).lower()
    if "served" not in joined or "83.60(2)" not in joined:
        raise GateFail(f"analyze reasons must name 'served' and § 83.60(2); got: {reasons}")
    ok("analyze -> escalation_needed=True with deterministic reasons naming 'served' + 83.60(2)")

    rows = call(
        "GET", f"{PROD}/api/deadline/{doc_id}/deadlines?session_id={session_id}",
        expect_status=200, headers={"x-api-key": api_key},
        validate=lambda d: "missing deadlines key" if not isinstance(d.get("deadlines"), list) else None,
    )
    if rows["deadlines"]:
        raise GateFail(f"escalated document must have ZERO deadline rows; got {len(rows['deadlines'])}")
    ok("deadlines -> zero rows while escalated (nothing fabricated)")

    # ── Leg B: supply service date → exactly one correct deadline ──────────
    expected_due = _add_business_days(date(2026, 8, 17), 5).isoformat()  # 2026-08-24
    put_body = json.dumps({"service_date": "2026-08-17", "service_method": "personal"}).encode()
    supplied = call(
        "PUT", f"{PROD}/api/deadline/{doc_id}/service-date?session_id={session_id}",
        expect_status=200, headers={"x-api-key": api_key, "Content-Type": "application/json"},
        body=put_body,
        validate=lambda d: "recompute != complete" if d.get("recompute") != "complete" else None,
    )
    got = supplied.get("deadlines") or []
    if len(got) != 1:
        raise GateFail(f"expected exactly 1 deadline after supply; got {len(got)}: {json.dumps(got)[:300]}")
    dl = got[0]
    if dl.get("due_date") != expected_due:
        raise GateFail(f"due_date {dl.get('due_date')!r} != independently computed {expected_due!r}")
    trace = dl.get("computation_trace") or ""
    if isinstance(trace, str):
        try:
            trace = json.loads(trace)
        except json.JSONDecodeError:
            pass
    trace_text = json.dumps(trace).lower()
    if "83.60(2)" not in trace_text:
        raise GateFail(f"computation_trace does not cite 83.60(2): {trace_text[:300]}")
    ok(f"supply -> exactly 1 deadline due {expected_due} "
       f"(independently computed 5 business days from 2026-08-17), trace cites 83.60(2)")

    # ── B5-f3: one provenance row, user_supplied ───────────────────────────
    sb_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
    }
    facts = call(
        "GET",
        f"{sb_url}/rest/v1/document_service_facts?document_id=eq.{doc_id}"
        "&select=service_date,service_method,provenance",
        expect_status=200, headers=sb_headers,
        validate=lambda d: "not a list" if not isinstance(d, list) else None,
    )
    if len(facts) != 1:
        raise GateFail(f"document_service_facts must hold exactly ONE row for the document; got {len(facts)}")
    fact = facts[0]
    if fact.get("provenance") != "user_supplied":
        raise GateFail(f"provenance must be 'user_supplied'; got {fact.get('provenance')!r}")
    if fact.get("service_date") != "2026-08-17":
        raise GateFail(f"service_date must be 2026-08-17; got {fact.get('service_date')!r}")
    ok("document_service_facts -> exactly 1 row, provenance='user_supplied', date=2026-08-17 (B5-f3)")

    print(f"\nB5 UI LIVE GATE — ALL LEGS GREEN (document {doc_id})\n")
    print("\n".join(evidence))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateFail as e:
        print(f"\nB5 UI LIVE GATE — FAILED: {e}")
        sys.exit(1)
