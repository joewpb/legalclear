# TASK: Enumerate every unauthenticated endpoint. Investigation only — change no code.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the sections for this item — do not read either file
end to end.

## The defect
DECISIONS.md, Group A item 2: "S1-x (auth sweep) The ~20 unauthenticated endpoints —
enumerate them with file:line before fixing, and report which are intentionally public."

AUDIT_FINDINGS.md §4.9 (verbatim):

| Gap | Where | Severity driver |
|---|---|---|
| Server-side `API_KEY` default `"testkey123"` | `config.py:30` | if Railway unset, all "protected" endpoints are open with a public string |
| Shared static key in JS bundle | `api.js:11` + 6 pages (`VITE_API_KEY`) | key is public by definition; architectural, known since IP A2 |
| `GET /api/deadline/{document_id}/deadlines` + `/trigger-events` | `deadline.py:43,62` | **no auth of any kind**; any document_id → that user's legal deadlines |
| `GET /document/{id}`, `GET /documents/{user_id}`, `POST /chat/{id}` | `routes.py:389-419` | key-gated but zero ownership check → any key holder reads anyone's docs/chats (IDOR; SL flagged this 2026-06-30, unchanged) |
| `GET /api/attorney-referral/users/{user_id}` | `attorney_referral.py:128` | no auth → full PII profile by UUID (latent until table exists) |
| `POST /api/attorney-referral/users` | `attorney_referral.py:88` | no auth; upsert keyed by client-supplied email → anyone can overwrite any profile |
| `POST /api/packet/{packet_id}/mark_paid` | `packet.py:163` | unauthenticated payment bypass (moot while payments off) |
| Unauthenticated LLM endpoints with **no rate limit** | `/api/chat/{module}` (`chat.py:57`), `/api/intake` (`intake.py:127`), `/api/forms/suggest` (`forms.py:503`), `/api/attorney-referral/intake` (`attorney_referral.py:138`), top-level `/eligibility` (`routes.py:165`), `/api/expungement/*`, `/api/landlord/*`, `/api/traffic/*` (`traffic.py:37`) | open cost exposure; the 10/min limiter covers only the 8 explainer/analyzer routes |
| Delete is correctly scoped | `routes.py:227-238` (`delete_document` requires session ownership) | positive control — proves the pattern exists and wasn't applied elsewhere |

## Scope
- Read-only inventory. Touch nothing except the named report file.
- Enumerate EVERY registered route in `backend/src/api/routes.py` and every router under
  `backend/src/api/routers/`. For each: (a) auth dependency (which `Depends(...)` or
  inline check guards it; name the function in `core/` if any), (b) rate limiter, if any,
  (c) LLM-backed or not (identify the agent/LLM call), (d) what data it touches.
- Produce one table: route | method | file:line | auth | rate limit | LLM | data touched.
- Then a classification table grouping every NO-AUTH route into: intentional public
  reference data / LLM cost surface / PII or tenancy exposure / payment-related /
  other-and-why. For "intentional public" claims, cite the doc or comment that says so —
  if nothing says so, classify as UNVERIFIED-INTENT.
- Also list every key-gated-but-no-ownership route (IDOR) — note only, do not fix
  (separate items).
- Check `frontend/src/api.js` and page components only to confirm which endpoints the
  shipped frontend actually calls (mark uncalled routes).

## Standing doctrines
- No code changes. No LLM calls. Read-only git commands only.
- uv for Python (you won't need it).

## Done means
Investigation only. Change no code. Report where the boundary sits, with file:line
evidence, what you verified versus inferred, and what remains UNVERIFIED. Write your
findings to runs/02_auth_sweep/REPORT.md (create it — that is the ONLY file you may write).
