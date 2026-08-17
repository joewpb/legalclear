# TASK: C2 — provider-agnostic email delivery adapter (Decision 8). Ships DARK.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-c2mail, branch fix/c2-email-adapter (checked out).

## Background (Decision 8, 2026-08-15)
Reminder emails currently terminate failed (no delivery provider). The
decision: a provider-agnostic delivery adapter; the concrete provider is
CONFIGURATION (recommendation: Resend). Without an API key, the adapter
ships DARK and reminders keep terminating failed until the key lands —
acceptable.

## Job
1. Find the reminder-termination path (grep for where deadline reminders
   fire/send/fail — likely a cron or scheduler module in backend/).
2. Author a delivery adapter module (e.g. backend/src/services/email_delivery.py):
   - Abstract base (or protocol): send_email(to, subject, body) -> bool.
   - Resend implementation using the requests/httpx client already in the
     stack, reading config: EMAIL_PROVIDER (default "resend"),
     RESEND_API_KEY, EMAIL_FROM.
   - A Noop/Logging provider as the fallback when config is absent.
   - Provider selection by config at call time.
3. Wire the reminder path to call the adapter. When no provider key is
   configured, the adapter logs and returns False — the existing
   "terminates failed" behavior stays intact (do NOT change the failed
   semantics; the reminder still records failure until a key lands).
4. Config: add the settings keys (backend/src/core/config.py) — EMAIL_PROVIDER,
   RESEND_API_KEY, EMAIL_FROM — with empty defaults. No secrets anywhere.

## Tests
- Provider selection: resend chosen when key present; logging fallback when
  absent.
- send_email failure → False and reminder path records the failure
  (mock the provider).
- No network calls in tests (mock the HTTP layer).

## Verification
cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 338/1 on main — must not drop. GREEN or STOP. (Copy
~/code/legalclear/backend/.env into the worktree backend/ if collection
fails on missing env — it is machine-local and gitignored.)
