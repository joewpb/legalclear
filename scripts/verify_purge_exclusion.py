#!/usr/bin/env python3
"""Verify the purge-exclusion predicate against live prod data (2026-08-24).

Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from backend/.env (never prints
them). Writes ONE throwaway fixture — an anonymous session backdated >72h with
a claim_facts row — then asserts that the NEW purge predicate would exclude it,
replicating the predicate client-side:

    delete from sessions s
    where s.user_id is null
      and s.created_at < now() - interval '72 hours'
      and not exists (claim_facts cf where cf.session_id = s.id)
      and not exists (claims c where c.session_id = s.id)

The fixture is DELETED at the end (cleanup is verified before exit), unless
--keep is passed (for a natural-fire probe: leave the row and wait for the
next 6-hourly cron tick, then confirm survival).

Usage: python3 scripts/verify_purge_exclusion.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request, parse, error

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> tuple[str, str]:
    url = ""
    key = ""
    env_path = REPO_ROOT / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k == "SUPABASE_URL":
                url = v.strip().strip("'\"")
            elif k == "SUPABASE_SERVICE_KEY":
                key = v.strip().strip("'\"")
    return url, key


def rest(url: str, key: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(f"{url}/rest/v1/{path}", data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode("utf-8", "replace")[:300]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true",
                        help="leave the fixture in place (natural-fire probe)")
    args = parser.parse_args()

    url, key = _load_env()
    if not url or not key:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY not found in backend/.env")
        return 2

    fixture_session = str(uuid.uuid4())
    backdated = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    # 1. Fixture: anonymous session backdated 9 days (well past the 72h fuse).
    status, body = rest(url, key, "POST", "sessions", {
        "id": fixture_session,
        "user_id": None,
        "created_at": backdated,
        "document_filename": "purge-exclusion-verify",
        "document_token_count": 0,
        "price_tier": "free",
        "price_paid_usd": 0,
        "payment_type": "free",
    })
    if status not in (200, 201):
        print(f"FAIL: could not create fixture session: HTTP {status} {body}")
        return 1
    print(f"1. fixture session created (id={fixture_session[:8]}…, created_at={backdated})")

    # 2. Attach a claim_facts row — the fact the purge must protect.
    status, body = rest(url, key, "POST", "claim_facts", {
        "session_id": fixture_session,
        "policy_inception_date": "2023-06-01",
        "provenance": "user_supplied",
    })
    if status not in (200, 201):
        print(f"FAIL: could not create fixture claim_facts: HTTP {status} {body}")
        rest(url, key, "DELETE", f"sessions?id=eq.{fixture_session}")
        return 1
    print("2. fixture claim_facts attached (policy_inception_date=2023-06-01, provenance=user_supplied)")

    # 3. Replicate the NEW purge predicate client-side against live data.
    status, purge_candidates = rest(
        url, key, "GET",
        f"sessions?select=id&user_id=is.null&created_at=lt.{parse.quote(cutoff, safe='')}",
    )
    if not isinstance(purge_candidates, list):
        print(f"FAIL: candidate query returned non-list: HTTP {status} {purge_candidates}")
        rest(url, key, "DELETE", f"claim_facts?session_id=eq.{fixture_session}")
        rest(url, key, "DELETE", f"sessions?id=eq.{fixture_session}")
        return 1
    candidates = {r["id"] for r in purge_candidates}
    status, facts_rows = rest(url, key, "GET", "claim_facts?select=session_id")
    protected_facts = {r["session_id"] for r in (facts_rows or [])}
    status, claim_rows = rest(url, key, "GET", "claims?select=session_id")
    protected_claims = {r["session_id"] for r in (claim_rows or []) if r.get("session_id")}
    purge_set = candidates - protected_facts - protected_claims

    print(f"3. predicate probe: candidates={len(candidates)} "
          f"fact_protected={len(protected_facts)} claim_protected={len(protected_claims)} "
          f"purge_set={len(purge_set)}")
    if fixture_session in purge_set:
        print("FAIL: fixture session WOULD be purged under the new predicate.")
        rest(url, key, "DELETE", f"claim_facts?session_id=eq.{fixture_session}")
        rest(url, key, "DELETE", f"sessions?id=eq.{fixture_session}")
        return 1
    if fixture_session not in candidates:
        print("FAIL: fixture session is not even a purge candidate (backdate didn't land).")
        rest(url, key, "DELETE", f"claim_facts?session_id=eq.{fixture_session}")
        rest(url, key, "DELETE", f"sessions?id=eq.{fixture_session}")
        return 1
    print(f"PASS: fixture session {fixture_session[:8]}… is excluded from the purge set "
          "(claim_facts protection) — the fact survives the predicate.")

    if args.keep:
        print(f"KEPT for natural-fire probe: {fixture_session}")
        return 0

    # 4. Cleanup (verified).
    status, _ = rest(url, key, "DELETE", f"claim_facts?session_id=eq.{fixture_session}")
    if status not in (200, 204):
        print(f"WARN: claim_facts cleanup HTTP {status}")
    status, _ = rest(url, key, "DELETE", f"sessions?id=eq.{fixture_session}")
    if status not in (200, 204):
        print(f"WARN: sessions cleanup HTTP {status}")
    status, check = rest(url, key, "GET", f"sessions?id=eq.{fixture_session}&select=id")
    print(f"4. cleanup: session present after delete = {bool(check)}")
    if check:
        print("FAIL: cleanup did not remove the fixture session.")
        return 1
    print("VERIFY PURGE EXCLUSION: PASS (fixture cleaned up)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
