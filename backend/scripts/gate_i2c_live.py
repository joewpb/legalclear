#!/usr/bin/env python3
"""I-2c live gate — four cases against the real POST /api/property-casualty/facts
endpoint and the real claim_facts table, keyed by session_id (Option A ruling
2026-08-20). Mirrors the B5 gate style (tests/test_decision6_worked_examples.py),
but this one talks to a live backend + prod DB, so Joe runs it manually after
the migration is applied.

Requires: the backend running (uv run uvicorn src.api.routes:app --port 8001)
and Supabase env vars configured.

Run: cd backend && uv run python scripts/gate_i2c_live.py
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.memory.db import DatabaseManager  # noqa: E402

BASE_URL = "http://localhost:8001"
FACTS_URL = f"{BASE_URL}/api/property-casualty/facts"
EXPLAIN_URL = f"{BASE_URL}/api/property-casualty/explain"

db = DatabaseManager()
failures = []


def _report(case: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {case}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(case)


def _new_session() -> str:
    """Run an explain call with no session_id so the backend creates one,
    and return the session_id it hands back — the real creation path."""
    resp = requests.post(
        EXPLAIN_URL,
        data={
            "sub_type": "first_party_property",
            "entities_json": "{}",
            "language": "en",
        },
        timeout=30,
    )
    resp.raise_for_status()
    for line in resp.text.splitlines():
        if line.startswith("data: ") and '"session_id"' in line:
            import json
            payload = json.loads(line[len("data: "):])
            if payload.get("session_id"):
                return payload["session_id"]
    raise RuntimeError(f"No session_id in explain response: {resp.text[:500]}")


def case_1_known_pre_cutoff():
    session_id = _new_session()
    resp = requests.post(FACTS_URL, json={
        "session_id": session_id,
        "policy_inception_date": "2022-01-01",
    }, timeout=10)
    ok = resp.status_code == 200
    body = resp.json() if ok else {}
    ok = ok and body.get("regime") == "pre" and body.get("provenance") == "user_supplied"
    _report("1. Known inception pre-2022-12-16 -> regime pre, provenance user_supplied", ok, str(resp.text))
    return session_id


def case_2_known_post_cutoff():
    session_id = _new_session()
    resp = requests.post(FACTS_URL, json={
        "session_id": session_id,
        "policy_inception_date": "2023-06-01",
    }, timeout=10)
    ok = resp.status_code == 200 and resp.json().get("regime") == "post"
    _report("2. Known inception post-2022-12-16 -> regime post", ok, str(resp.text))
    return session_id


def case_3_unknown_escalates():
    session_id = _new_session()
    # No facts row written at all for this session — absent, not just null.
    explain_resp = requests.post(
        EXPLAIN_URL,
        data={
            "sub_type": "first_party_property",
            "entities_json": '{"date_of_loss": "2024-01-01"}',
            "language": "en",
            "session_id": session_id,
        },
        timeout=30,
    )
    ok = explain_resp.status_code == 200
    # The rendered contract is the FINAL payload chunk (the client parses the
    # last complete payload and renders it; the raw model stream is
    # transitional). Deterministic boundary: the post-stream block pops
    # key_deadlines when regime is unknown, so the final payload must not
    # carry one. The leading session chunk carries regime + guidance.
    final_payload = None
    for line in explain_resp.text.splitlines():
        if line.startswith("data: "):
            candidate = line[len("data: "):]
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if "session_id" not in parsed and "sub_type_identified" in parsed:
                final_payload = parsed
    meta_chunk = None
    for line in explain_resp.text.splitlines():
        if line.startswith("data: "):
            try:
                parsed = json.loads(line[len("data: "):])
            except Exception:
                continue
            if parsed.get("type") == "session":
                meta_chunk = parsed
                break
    ok = ok and meta_chunk is not None
    ok = ok and meta_chunk.get("claim_regime", {}).get("regime") == "unknown"
    ok = ok and "guidance" in json.dumps(meta_chunk)
    ok = ok and (final_payload is None or "key_deadlines" not in final_payload)
    text = json.dumps(meta_chunk)[:500]
    _report("3. Unknown (absent) -> escalated, regime unknown, guidance present, no regime content", ok, explain_resp.text[:500])
    return session_id


def case_4_recompute_survives(session_id: str):
    """Capture a fact, then run the explain flow again (recompute) — the
    user-supplied value must survive untouched, exactly as B5-f3 requires
    of document_service_facts."""
    requests.post(FACTS_URL, json={
        "session_id": session_id,
        "policy_inception_date": "2021-03-01",
    }, timeout=10).raise_for_status()
    before = db.get_claim_fact(session_id)

    requests.post(
        EXPLAIN_URL,
        data={
            "sub_type": "first_party_property",
            "entities_json": '{"date_of_loss": "2024-01-01"}',
            "language": "en",
            "session_id": session_id,
        },
        timeout=30,
    ).raise_for_status()

    after = db.get_claim_fact(session_id)
    ok = before == after and after is not None and after.get("policy_inception_date") == "2021-03-01"
    _report("4. Explain rerun (recompute) after capture -> user value survives unchanged", ok, f"before={before} after={after}")


def main():
    if db.client is None:
        print("FAIL — Supabase not configured; cannot run live gate")
        sys.exit(1)

    case_1_known_pre_cutoff()
    case_2_known_post_cutoff()
    case_3_unknown_escalates()
    session_id = _new_session()
    case_4_recompute_survives(session_id)

    if failures:
        print(f"\n{len(failures)} case(s) failed: {failures}")
        sys.exit(1)
    print("\nAll 4 cases passed.")


if __name__ == "__main__":
    main()
