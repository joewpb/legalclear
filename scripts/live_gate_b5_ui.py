#!/usr/bin/env python3
"""B5 UI live gate — two legs against prod (S2-7 UI half, scope 2026-08-30).

Leg A (escalation leg): upload a summons fixture whose only date is an
issuance line ("DATED this 14th day of August, 2026") → analyze → the anchor
gate MUST escalate (escalation_needed, reasons naming the missing 'served'
anchor for whichever served-anchored rule the classifier routed to — the
engine must never substitute the issuance date). Zero deadline rows. This is
the ask-the-user half firing.

Leg B (supply leg): PUT service-date 2026-08-17 / personal → exactly ONE
deadline whose due date is computed INDEPENDENTLY here from the SUPPLIED
service date under the rule Leg A cited (5 business days for § 83.60(2);
20 calendar days for 1.140(a)) — never by trusting the engine — and MUST
NOT equal the issuance-anchored date (the S2-7 anti-substitution assertion).
Trace cites the rule; document_service_facts holds exactly one row with
provenance 'user_supplied' (B5-f3 single-row invariant).

S3-5E discipline: every call declares a status expectation AND a content
validator; no expect=None. Any failed assertion aborts with evidence printed.

Runs against the live Railway backend; creds read from backend/.env
(API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY) — values never printed.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
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


def _add_calendar_days(start: date, n: int) -> date:
    return start + timedelta(days=n)


# The two served-anchored rules the LLM classifier/extractor can route this
# fixture to (both are correct escalations; the rule choice is model-driven):
#   civil_summons → Fla. R. Civ. P. 1.140(a): 20 CALENDAR days after service
#   83.60(2)      → Fla. Stat. § 83.60(2):       5 BUSINESS days after service
SERVED_RULES = {
    "1.140(a)": {"days": 20, "counting": "calendar", "label": "Answer to Civil Summons"},
    "83.60(2)": {"days": 5, "counting": "business", "label": "Answer to Residential Eviction Complaint"},
}

SERVICE_DATE = date(2026, 8, 17)
ISSUANCE_DATE = date(2026, 8, 14)

for _rule in SERVED_RULES.values():
    _counting = _rule["counting"]
    _rule["expected_due"] = (
        _add_business_days(SERVICE_DATE, _rule["days"])
        if _counting == "business"
        else _add_calendar_days(SERVICE_DATE, _rule["days"])
    ).isoformat()
    _rule["issuance_anchored_due"] = (
        _add_business_days(ISSUANCE_DATE, _rule["days"])
        if _counting == "business"
        else _add_calendar_days(ISSUANCE_DATE, _rule["days"])
    ).isoformat()


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
    ok("upload -> document_id + session_id returned (status 200)")
    doc_id, session_id = up["document_id"], up["session_id"]

    analyze = call(
        "POST", f"{PROD}/api/deadline/analyze/{doc_id}",
        expect_status=200, headers={"x-api-key": api_key},
        validate=lambda d: "escalation_needed is not True" if not d.get("escalation_needed") else None,
    )
    reasons = analyze.get("escalation_reasons") or []
    joined = " ".join(reasons).lower()
    cited = [cite for cite in SERVED_RULES if cite.lower() in joined]
    if "served" not in joined:
        raise GateFail(f"escalation reasons must name the missing 'served' anchor; got: {reasons}")
    if not cited:
        raise GateFail(
            f"escalation must cite a served-anchored rule ({', '.join(SERVED_RULES)}); got: {reasons}"
        )
    esc_rule = cited[0]
    ok(f"analyze -> escalation_needed=True, reasons name the missing 'served' "
       f"anchor for {esc_rule} (never substituted, never silent)")

    rows = call(
        "GET", f"{PROD}/api/deadline/{doc_id}/deadlines?session_id={session_id}",
        expect_status=200, headers={"x-api-key": api_key},
        validate=lambda d: "missing deadlines key" if not isinstance(d.get("deadlines"), list) else None,
    )
    if rows["deadlines"]:
        raise GateFail(f"escalated document must have ZERO deadline rows; got {len(rows['deadlines'])}")
    ok("deadlines -> zero rows while escalated (nothing fabricated)")

    # ── Leg B: supply service date → exactly one correct deadline ──────────
    # The expected due date follows the rule that escalated in Leg A — both
    # expectations are computed INDEPENDENTLY here from the SUPPLIED service
    # date, never by trusting the engine, and never from the issuance date.
    expected_due = SERVED_RULES[esc_rule]["expected_due"]
    issuance_anchored = SERVED_RULES[esc_rule]["issuance_anchored_due"]
    put_body = json.dumps({
        "service_date": SERVICE_DATE.isoformat(),
        "service_method": "personal",
    }).encode()
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
        raise GateFail(f"due_date {dl.get('due_date')!r} != independently computed {expected_due!r} "
                       f"for {esc_rule} from service date {SERVICE_DATE}")
    if dl.get("due_date") == issuance_anchored:
        raise GateFail(
            f"S2-7 VIOLATION: due_date {dl.get('due_date')!r} equals the issuance-anchored date "
            f"{issuance_anchored!r} — the wrong anchor was used"
        )
    trace = dl.get("computation_trace") or ""
    if isinstance(trace, str):
        try:
            trace = json.loads(trace)
        except json.JSONDecodeError:
            pass
    trace_text = json.dumps(trace).lower()
    if esc_rule.lower() not in trace_text:
        raise GateFail(f"computation_trace does not cite {esc_rule}: {trace_text[:300]}")
    ok(f"supply -> exactly 1 deadline due {expected_due} (independently computed from "
       f"service {SERVICE_DATE} under {esc_rule}), trace cites {esc_rule}, "
       f"issuance-anchored {issuance_anchored} NOT used")

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
    if fact.get("service_date") != SERVICE_DATE.isoformat():
        raise GateFail(f"service_date must be {SERVICE_DATE}; got {fact.get('service_date')!r}")
    ok(f"document_service_facts -> exactly 1 row, provenance='user_supplied', "
       f"date={SERVICE_DATE} (B5-f3)")

    print(f"\nB5 UI LIVE GATE — ALL LEGS GREEN (document {doc_id})\n")
    print("\n".join(evidence))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GateFail as e:
        print(f"\nB5 UI LIVE GATE — FAILED: {e}")
        sys.exit(1)
