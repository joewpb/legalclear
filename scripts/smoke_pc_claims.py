#!/usr/bin/env python3
"""Phase I finale — live P&C smoke test against prod (honest harness).

Harness rule (2026-08-24, FOLLOW_UPS silent-check instance #4): every call
MUST declare an expectation — a status code via `expect`, or a content
validator for raw bodies. `expect=None` is an error, not a pass: the first
version of this script recorded the PDF-artifact 500s as passes and printed
"ALL PASS" while two prod defects were live. That failure mode is banned.
"""
import json
import sys
import urllib.parse
import urllib.request
import urllib.error

BASE = "https://zesty-delight-production-b533.up.railway.app"
results = []


def _fail(name, evidence):
    results.append((name, False, evidence))
    return False


def _pass(name, evidence=""):
    results.append((name, True, evidence))
    return True


def call(method, path, body=None, expect=None, validate=None, label=None):
    """One HTTP call. REQUIRES `expect` (status) or `validate` (content fn).

    `validate` receives the raw response bytes and must return True or a
    failure description. Raw calls (validate set) never fake a pass from
    status alone. No expectation supplied = harness error (loud).
    """
    name = label or f"{method} {path}"
    if expect is None and validate is None:
        raise RuntimeError(f"HARNESS ERROR: no expectation declared for {name}")
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            payload, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        payload, status = e.read(), e.code
    if expect is not None and status != expect:
        return _fail(name, f"status {status} != {expect}: {payload[:160]!r}")
    if validate is not None:
        verdict = validate(payload)
        if verdict is not True:
            return _fail(name, f"content check failed: {verdict} (status {status})")
        return _pass(name, f"status {status}, {len(payload)} bytes")
    return _pass(name, f"status {status}")


# ── Test-the-tester (FOLLOW_UPS silent-check instance #5 closure) ──────────
# A check that can pass silently is not a check — including the harness that
# enforces that rule. `--selftest` runs a KNOWN-FAIL scenario against a stub
# transport and asserts the harness reports it as FAIL (and that a
# no-expectation call raises instead of passing). Exits 0 only when the
# harness fails loudly as designed; CI exercises it via
# backend/tests/test_smoke_harness.py.
def _selftest() -> int:
    results.clear()
    import urllib.request as _ur

    class _Stub500:
        status = 500
        def read(self):
            return b'{"detail": "stub 500"}'
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    _ur.urlopen = lambda req, timeout=60: _Stub500()

    errors = []

    # 1. Known-fail scenario: expectation 200, stub delivers 500.
    call("GET", "/selftest/known-fail", expect=200, label="selftest known-fail")

    # 2. Known-pass scenario: expectation 500, stub delivers 500.
    call("GET", "/selftest/known-pass", expect=500, label="selftest known-pass")

    # 3. No expectation at all must raise (instance #4 ban: expect=None).
    try:
        call("GET", "/selftest/no-expectation")
        errors.append("call() with no expectation did NOT raise")
    except RuntimeError:
        pass

    fails = [r for r in results if not r[1]]
    names = [r[0] for r in fails]
    if "selftest known-fail" not in names:
        errors.append("known-fail scenario was not recorded as FAIL")
    elif not any("status 500 != 200" in (r[2] or "") for r in fails):
        errors.append("known-fail evidence missing the status mismatch")
    passes = [r for r in results if r[1]]
    if "selftest known-pass" not in [r[0] for r in passes]:
        errors.append("known-pass scenario was not recorded as PASS")
    if len(results) != 2:
        errors.append(f"expected exactly 2 recorded results, got {len(results)}")

    if errors:
        print("SELFTEST FAIL — the harness can still pass silently:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SELFTEST PASS — known-fail scenario reported FAIL; no-expectation "
          "call raised; tally keyed on the ok flag. Harness fails loudly as designed.")
    return 0


if "--selftest" in sys.argv:
    sys.exit(_selftest())


def _is_pdf(b: bytes):
    return True if b[:5] == b"%PDF-" else f"not a PDF: {b[:60]!r}"


def _has_vevent(b: bytes):
    if b"BEGIN:VCALENDAR" not in b:
        return f"not VCALENDAR: {b[:60]!r}"
    if b"BEGIN:VEVENT" not in b:
        return "VCALENDAR but no VEVENT (empty deadline calendar)"
    return True


def _json(resp: bytes):
    return json.loads(resp)


# 1. Create claim — date_of_loss must persist (I-4 fix).
req = urllib.request.Request(BASE + "/api/claims",
                             data=json.dumps({"peril": "fire", "date_of_loss": "2026-08-01"}).encode(),
                             method="POST")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        created_raw, status = r.read(), r.status
except urllib.error.HTTPError as e:
    created_raw, status = e.read(), e.code
if status != 200:
    _fail("1. create claim", f"status {status}: {created_raw[:160]!r}")
else:
    created = json.loads(created_raw)
    code, session_id = created.get("code"), created.get("session_id")
    if not code or not session_id:
        _fail("1. create claim", f"no code/session: {created}")
    else:
        _pass("1. create claim", f"code={code[:8]}… session={'SET' if session_id else 'MISSING'}")

# 2. Policy inception (post regime)
call("POST", "/api/property-casualty/facts",
     {"session_id": session_id, "policy_inception_date": "2023-01-01"},
     expect=200, label="2. policy inception fact")

# 3. Guide — deadlines must be non-empty (was defect 2: always [])
def _guide_ok(b: bytes):
    g = json.loads(b)
    if g.get("claim_regime", {}).get("regime") != "post":
        return f"regime {g.get('claim_regime')} != post"
    dls = g.get("deadlines") or []
    if not dls:
        return "deadlines empty (date_of_loss still not reaching the engine)"
    if not g.get("disclaimer"):
        return "disclaimer missing"
    if not g.get("red_flag_catalog"):
        return "red_flag_catalog missing"
    return True

call("GET", f"/api/claims/{code}/guide", validate=_guide_ok,
     label="3. guide: regime+deadlines+disclaimer")

# 4. Events: claim number + two red flags
for trig in ("claim_number_received", "reservation_of_rights_letter", "siu_contact"):
    call("POST", f"/api/claims/{code}/events", {"trigger_name": trig}, expect=200,
         label=f"4. event {trig}")

# 5. Escalation after 2 flags
def _esc_ok(b: bytes):
    g = json.loads(b)
    esc = g.get("escalation") or {}
    if esc.get("active_count") != 2:
        return f"escalation active_count {esc.get('active_count')} != 2"
    if "fire.p1.first_week" not in (g.get("state", {}).get("active_phase_ids") or []):
        return f"p1 not active: {g.get('state', {}).get('active_phase_ids')}"
    return True

call("GET", f"/api/claims/{code}/guide", validate=_esc_ok,
     label="5. escalation + p1 active")

# 6. Artifact catalog
def _catalog_ok(b: bytes):
    c = json.loads(b)
    n = len(c.get("artifacts", {}))
    return True if n == 12 else f"catalog has {n} artifacts (expected 12)"

call("GET", f"/api/claims/{code}/artifacts", validate=_catalog_ok, label="6. artifact catalog")

# 7. Save details
call("POST", f"/api/claims/{code}/details",
     {"details": {"insured_name": "Jane Smoke Test", "insured_address": "1 Test Way, Miami, FL 33101",
                  "insurer_name": "Test Insurance Co.", "claim_number": "SMOKE-002",
                  "policy_number": "POL-SMOKE-2"}},
     expect=200, label="7. save details")

# 8-9. PDF artifacts — content-validated, never status-only
call("GET", f"/api/claims/{code}/artifacts/claim_log", validate=_is_pdf,
     label="8. claim_log PDF")
call("GET", f"/api/claims/{code}/artifacts/policy_request_letter", validate=_is_pdf,
     label="9. policy_request_letter PDF")

# 10. ICS — must contain at least one VEVENT now that deadlines compute
call("GET", f"/api/claims/{code}/artifacts/deadline_calendar_ics", validate=_has_vevent,
     label="10. deadline calendar ICS")

# 11. Snapshot
def _snap_ok(b: bytes):
    s = json.loads(b)
    if not s.get("disclaimer"):
        return "disclaimer missing"
    return True

call("GET", f"/api/claims/{code}", validate=_snap_ok, label="11. snapshot + disclaimer")

# 12. Unknown code 404
call("GET", "/api/claims/not-a-real-code-xyz", expect=404, label="12. unknown code 404")

# 13. Bad trigger 422
call("POST", f"/api/claims/{code}/events", {"trigger_name": "definitely_not_a_trigger"},
     expect=422, label="13. unknown trigger 422")

# 14. LLM tap — Anthropic is zero-credit; the tap must degrade to an
# explicit error payload or return a complete definition. Either is a pass;
# a 200 with neither definition nor error is a silent failure and fails.
def _tap_ok(b: bytes):
    t = json.loads(b)
    if t.get("error"):
        return True
    if t.get("definition") and t.get("citations") is not None:
        return True
    return f"tap 200 without definition or error: {list(t)[:6]}"

form = urllib.parse.urlencode({"term": "ACV"}).encode()
req = urllib.request.Request(BASE + "/api/property-casualty/tap/define-term", data=form, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        tap_raw, tap_status = r.read(), r.status
except urllib.error.HTTPError as e:
    tap_raw, tap_status = e.read(), e.code
if tap_status == 200:
    _pass("14. tap degrade-or-answer", _tap_ok(tap_raw) is True and "200" or str(_tap_ok(tap_raw)))
else:
    _fail("14. tap degrade-or-answer", f"status {tap_status}")

# ── Report ──
# Tally on r[1] (the ok flag), NOT r[2] (the evidence string — always
# truthy, which silently turned every FAIL into a pass on 2026-08-24).
fails = [r for r in results if not r[1]]
print("\n=== SMOKE RESULTS ===")
for name, ok, ev in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {ev}")
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
if fails:
    print("FAILURES:", [r[0] for r in fails])
    sys.exit(1)
print("SMOKE: ALL PASS (honest harness)")
