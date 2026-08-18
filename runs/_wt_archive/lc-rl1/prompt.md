# Dispatch RL-1 — XFF/X-Real-IP-aware rate-limit key (slowapi)

Repo: joewpb/legalclear. Worktree: ~/code/lc-rl1 (branch fix/rl1-xff-key, cut from origin/main bbee714).

## Context (orchestrator-verified facts)

- backend/src/api/limiter.py is the ONLY limiter definition:
  `limiter: Limiter = Limiter(key_func=get_remote_address)` (slowapi).
- slowapi's get_remote_address returns request.client.host and does NOT parse
  X-Forwarded-For. Behind Railway's edge proxy, request.client is the proxy
  hop, so the three existing @limiter.limit("10/minute") surfaces
  (wills_trusts.py:52, property_casualty.py:20, small_claims.py:60) all share
  one bucket keyed on the proxy IP.
- VERIFIED from Railway's official docs (Specs & Limits, public networking):
  the edge provides **`X-Real-IP` — "for identifying client's remote IP"**.
  `X-Forwarded-For` is NOT in Railway's documented header set. Do not assume
  an XFF format exists in prod; do not assume it doesn't in other contexts.

## Part 1 — design the key_func (report-first, VERIFIED vs INFERRED labels)

1. Read backend/src/api/limiter.py and every @limiter.limit call site
   (grep -rn "limiter.limit" backend/). Report the current wiring.
2. Design a key_func with this priority order and justify each step:
   a. `X-Real-IP` header value, when present and a valid IP (Railway edge sets
      it from the actual client connection — this is the prod path).
   b. Fallback: the LEFTMOST IP of `X-Forwarded-For`, only when X-Real-IP is
      absent (covers other proxies / local dev; never the prod path).
   c. Final fallback: request.client.host (direct connections, unit tests).
   CRITICAL hardening (this is the spoofing requirement): when X-Real-IP is
   present, IGNORE the XFF chain entirely — a caller-supplied spoofed XFF must
   not influence the bucket key.
3. Sanity-check edge cases and state how each is handled: IPv6 literals,
   malformed header values, whitespace, XFF entries with ports, empty header.

## Part 2 — implement + test

1. Rewrite limiter.py: keep the shared `limiter` object, replace the key_func.
   Implement the key function IN limiter.py (or a small sibling module it
   imports — your call) with a pure helper `_client_ip(request) -> str` that is
   unit-testable WITHOUT a live server.
2. Add tests in backend/tests/test_limiter_xff.py covering AT MINIMUM:
   a. Two different client IPs behind the same proxy (same request.client
      host, different X-Real-IP) produce DIFFERENT keys → separate buckets.
   b. A spoofed X-Forwarded-For does NOT change the key when X-Real-IP is
      present (attacker cannot bypass their own limit by spoofing).
   c. No X-Real-IP → leftmost XFF used; malformed XFF → falls through to
      request.client.
   d. The existing 3 limit decorators still resolve the limiter without
      import errors.
   Use a fake request object (SimpleNamespace with .headers and .client
   attributes) — no test server needed.
3. Confirm slowapi's storage backend: inspect the installed slowapi package
   (uv run python -c "import slowapi, inspect; ..." or read site-packages) for
   the default storage when storage_uri is not set. Report VERIFIED whether
   limits live in per-process memory (i.e., reset on every Railway
   deploy/restart) — say it plainly, this goes in the phase report.
4. Run the suite with the CI-scope ignores from .github/workflows/pytest.yml.
   Baseline: 352 passed, 1 skipped. New tests add to the count; zero NEW
   failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network (no
curl, no WebFetch). No railway/supabase commands. Edit in place — the
orchestrator commits. Do not change any @limiter.limit value; do not add
decorators to new routes (that is a separate dispatch). Do not touch routes.py.
Final answer: key_func design with justification, test list + results, storage
backend verdict, files changed, turn count.
