# S1-5 Data-Flow Map: User Data → DeepSeek

**Run:** 07_deepseek · **Date:** 2026-08-13 · **Repo state:** main @ 26e282c (audit baseline 0c2e006 + doc commits)
**Mode:** Investigation only. No code changed. Only this file written.
**Provider (all three call-sites):** `POST https://api.deepseek.com/v1/chat/completions`, model `deepseek-chat`, key from `settings.DEEPSEEK_API_KEY` (`backend/src/core/config.py:30`, default `""`).

## TL;DR

| # | Call-site | User data sent to DeepSeek | Trigger | Prod liveness |
|---|---|---|---|---|
| 1 | `opinion_retrieval.py:255` (`generate_attorney_questions`) | **Yes — LLM-derived legal content from the user's uploaded police report** (findings, ask-attorney text, charges). No direct name/email/phone fields, but findings can quote names from the report. | `POST /api/police-report/analyze` (PoliceReportAnalyzer page); `POST /api/criminal/explain` sends **effectively no user data** (see §1.2) | **UNVERIFIABLE-FROM-REPO** — code path is unconditionally reached in prod; fires iff `DEEPSEEK_API_KEY` is set in Railway (unverified, audit Q1) |
| 2 | `attorney_referral.py:217` (intake fallback) | **Yes — worst case: direct PII.** The full intake conversation, which by design collects name, case narrative, email, phone. | `POST /api/attorney-referral/intake` (AttorneyReferralFL page, soft-launched) | **LATENT** — fallback only; fires only if Anthropic key missing/call fails AND DeepSeek key set |
| 3 | `orin_opinions.py:171` (batch metadata) | **No user data.** Only first 600 chars of *public court opinions*. User tags shape the SQL query but are not sent to DeepSeek. | Fallback inside call-site 1's retrieval when Supabase returns < 3 opinions | **DEAD in prod (Railway)** — requires SSH to Joe's Tailscale box; live only from Joe's dev machine |

**Disclosure: none anywhere.** `docs/TERMS_OF_SERVICE.md` §7 names Stripe, Supabase, and Anthropic as third-party services — DeepSeek is absent. No frontend string, README, or CLAUDE.md mention exists. `DEEPSEEK_API_KEY` is also absent from `backend/.env.example` (violating the "all required env var names" constraint if the key is considered production config).

**Retention on our side:** DeepSeek *output* is streamed to the client and never persisted server-side (verified: no DB writes in the police-report/criminal stream paths; no localStorage in the frontend pages). The attorney-referral conversation (the *input* that may have transited DeepSeek) **is** persisted — to `user_profiles` and `attorney_inquiries` in Supabase — but that persistence is independent of which provider answered. **Retention on DeepSeek's side: unknowable from the repo** — governed by DeepSeek's ToS/privacy policy (PRC-based processor); the code sends no opt-out/no-train headers or parameters.

---

## 1. Call-site 1 — `backend/src/services/opinion_retrieval.py` `generate_attorney_questions()` (POST at :255)

### 1.1 Trigger path

Two agents call `generate_attorney_questions(parsed, opinions)` after their Claude stream completes:

- **Police Report Analyzer** — `backend/src/agents/police_report_v2.py:366-368`, reached from `POST /api/police-report/analyze` (`backend/src/api/routers/police_report.py:35-62`, SSE streaming, rate-limited 10/min, **no auth**). Frontend: `frontend/src/pages/PoliceReportAnalyzer.tsx:534`.
- **Criminal Procedure Explainer** — `backend/src/agents/criminal_procedure.py:192-194`, reached from `POST /api/criminal/explain` (`backend/src/api/routers/criminal.py:48-60`). Frontend: `frontend/src/pages/CriminalProcedureExplainer.tsx:377`.

Both routers are registered in `routes.py:108,114`. The batch legacy endpoint `POST /api/police-report/analyze/batch` (`police_report.py:70`) does **not** reach this call-site (it uses `scan_documents`, not the v2 streaming agent).

### 1.2 Fields sent

Prompt construction, `opinion_retrieval.py:233-251`:

```python
discrepancies = analysis_result.get("discrepancies", [])
charges = analysis_result.get("charges_explained", [])
ctx = "User situation:\n"
for d in discrepancies[:5]:
    ctx += f"  - Finding: {d.get('finding','')}. Ask attorney about: {d.get('ask_attorney','')}\n"
for c in charges[:3]:
    ctx += f"  - Charge: {c.get('charge','')}\n"
opinions_text = ""
for i, op in enumerate(opinions[:5]):
    opinions_text += (f"--- OPINION {i} ---\n"
                      f"Case: {op.get('case_name','')}\n"
                      f"Court: {op.get('court','')}\n"
                      f"Summary: {op.get('summary_plain','')[:300]}\n\n")
```

The full user message (`opinion_retrieval.py:265-285`) = fixed instructions + `ctx` + `opinions_text`.

Classification of what crosses the wire:

- **Direct PII (name/phone/email):** not sent as structured fields. **Caveat:** `finding`, `ask_attorney`, and `charge` are free text authored by Claude *from the user's actual uploaded police report*, and police-report findings routinely name the defendant, officers, and witnesses ("Officer Smith states Mr. García refused…"). So incidental direct PII is plausible, not guaranteed.
- **Legal-content data (sent):** up to 5 discrepancy findings + attorney-question stubs and up to 3 charges — i.e. a synthesized summary of the user's criminal exposure and the defects in their arrest paperwork. This is derived/synthesized text (Claude's Stage-1 output), **not** raw document text.
- **Public data (sent):** case name / court / 300-char summary of up to 5 published FL opinions.

**Criminal-procedure caller nuance (verified):** the criminal explainer's JSON schema (`criminal_procedure.py:42-50`) has **no** `discrepancies` or `charges_explained` keys, so both `.get()` calls return `[]` and `ctx` collapses to the literal string `"User situation:\n"`. On the `/api/criminal/explain` path, the DeepSeek prompt therefore contains **no user data at all** — only public opinion summaries. Note `charge_type`/`severity`/`current_stage` (the user's actual inputs) are *not* included. The user-data exposure at this call-site comes solely from the police-report path.

### 1.3 Provider, model, missing-key behavior

- Endpoint `https://api.deepseek.com/v1/chat/completions` (`:256`), model `"deepseek-chat"` (`:262`), `max_tokens: 600`, `temperature: 0.3`, `timeout=15`, via `requests` (sync, wrapped in `asyncio.to_thread` by both callers).
- Key: `settings.DEEPSEEK_API_KEY` (`:229`); `config.py:30` defaults to `""`.
- **Missing key → silent skip**, no exception, no Anthropic fallback: `if not key or not opinions: return opinions` (`:229-231`). Opinions are returned with their corpus-stored generic `attorney_prompt` values. Any request/parse exception is caught and logged (`:305-306`); opinions returned unchanged.

### 1.4 Retention

- Response use: DeepSeek's JSON array is written into the in-memory opinion dicts as `attorney_explanation` / `attorney_prompt` (`:297-304`), then streamed to the client as the `relevant_opinions` SSE event (`police_report_v2.py:369-374`; `criminal_procedure.py:195-200`).
- **No server-side persistence**: no `DatabaseManager`/Supabase write exists in `police_report_v2.py` or `criminal_procedure.py` post-stream paths (grep-verified — the only `supabase` hit in `police_report_v2.py` is a comment at :359). The Supabase `legal_opinions.attorney_prompt` column is *read* but never written back.
- **No client-side persistence**: `PoliceReportAnalyzer.tsx` has no `localStorage`/`sessionStorage` usage (grep-verified); results live in React state only.
- Logs: failures log a warning with traceback (`:306`) — no prompt content is logged. The tag-derivation log lines (`:501-505`, `:556-561`) intentionally log flags/tags only ("No PII" per in-code comment).

### 1.5 Liveness — **UNVERIFIABLE-FROM-REPO**

The code path is unconditionally reached on every police-report analysis in prod (Railway `zesty-delight`). Whether the DeepSeek POST actually fires depends entirely on `DEEPSEEK_API_KEY` being set in Railway, which the item-0 recon could not verify (AUDIT_FINDINGS.md §7 Q1). If unset: silent skip, generic prompts, feature degrades invisibly. The key **is** set in local `backend/.env` (line 18, presence verified, value not read), so the path is LIVE from Joe's dev machine.

## 2. Call-site 2 — `backend/src/api/routers/attorney_referral.py` `_call_ai()` DeepSeek fallback (POST at :217)

(The audit cites `:224`; at current HEAD the `httpx` POST spans `:217-229` — same call-site.)

### 2.1 Trigger path

`POST /api/attorney-referral/intake` (`attorney_referral.py:138-155`, **no auth, no rate limit decorator**) → `_call_ai(messages)` (`:185`). Router registered at `routes.py:123`. Frontend: `frontend/src/pages/AttorneyReferralFL.tsx:33` (route `/attorney-referral`, `App.tsx:92`; linked from `FindLegalHelpFL.tsx:204` and `caselaw/types.ts:91` — soft-launched, no main-nav tile per audit Q6).

### 2.2 Fields sent

The client sends the **entire conversation so far** on every turn (`AttorneyReferralFL.tsx:36`: `body: JSON.stringify({ conversation: updated, user_id: userId })`). The backend forwards it wholesale:

```python
# attorney_referral.py:142-145
messages = [
    {"role": "system", "content": _SYSTEM_PROMPT},
    *req.conversation,
]
# :223-228 (DeepSeek branch)
json={
    "model": "deepseek-chat",
    "messages": messages,   # ← full conversation incl. system prompt
    ...
}
```

The system prompt (`:67-83`) *instructs the AI to collect*: name (stage 1), case type (stage 2), what happened / when / where / who involved (stage 3), **email + phone** (stage 4). So by design, a conversation deep in the intake contains:

- **Direct PII:** full name, email, phone number — verbatim, as typed by the user.
- **Legal-content data:** the user's own narrative of their legal problem (eviction, injury, criminal, etc.), dates, locations, parties.
- **Synthesized text:** prior assistant turns (which may restate the PII in the stage-5 summary).

This is the **highest-exposure call-site of the three**.

### 2.3 Provider, model, missing-key behavior

- DeepSeek is the **fallback**, not the primary: `_call_ai` tries Anthropic `claude-haiku-4-5` first (`:188-211`) and reaches DeepSeek only when `_ANTHROPIC_KEY` is falsy **or** the Anthropic call raises/non-200s in a way that falls through (`:213-236`). Model `"deepseek-chat"`, `max_tokens: 300`, `temperature: 0.7`, `timeout=30`, via `httpx`.
- Both keys read once at import (`:32-33`) from `settings`.
- DeepSeek key missing → branch skipped; if Anthropic also unavailable → hard-coded apology + FL Bar phone number (`:239-244`). No exception surfaces.

### 2.4 Retention

- Response use: returned to the client as the next assistant turn (`IntakeResponse`, `:150-155`). The `/intake` endpoint itself **writes nothing** to the DB (stateless by design, `:4-6`).
- **But the conversation is persisted downstream**, provider-agnostic:
  - `POST /users` upserts `email, full_name, phone, case_category, case_summary, urgency` into Supabase `user_profiles` (`:106-123`).
  - `POST /submit` inserts the **full conversation array** + summary into `attorney_inquiries` (`:167-174`, `AttorneyReferralFL.tsx:56-63`).
  - So if a turn transited DeepSeek, both the user's inputs and DeepSeek's outputs (as assistant turns) end up stored in Supabase. Related known issue: these tables/endpoints are unauthenticated (S1-2/S1-3, out of scope here).
- Client-side: React state only; no localStorage (grep-verified in `AttorneyReferralFL.tsx`).
- Logs: failures log the exception only (`:236`), not the messages.

### 2.5 Liveness — **LATENT**

Requires **two** conditions in Railway: `DEEPSEEK_API_KEY` set (UNVERIFIED, audit Q1) **and** the Anthropic branch failing (key unset — implausible, the whole product depends on it — or a transient Anthropic outage/exception). In normal prod operation this path should never fire; it is a live-wire fallback that activates precisely during Anthropic incidents. Mark LATENT: dormant but armed if the key is set.

## 3. Call-site 3 — `backend/src/services/orin_opinions.py` `_batch_extract_metadata()` (POST at :171)

(The audit cites `:178`; at current HEAD the `requests.post` spans `:171-194` — same call-site.)

### 3.1 Trigger path

Not directly HTTP-exposed. `search_orin_opinions()` (`:236`) is called only as the last-resort fallback inside `get_relevant_opinions()` when Supabase returns fewer than `limit` opinions (`opinion_retrieval.py:192-207`). So its ultimate triggers are the same two endpoints as call-site 1 (`/api/police-report/analyze`, `/api/criminal/explain`). Inside it, `_batch_extract_metadata(raw_opinions)` runs at `:314` after the psql query succeeds.

### 3.2 Fields sent — **no user data**

Prompt construction, `:164-189`:

```python
headers_text = ""
for i, op in enumerate(opinions[:10]):
    headers_text += f"--- OPINION {i} ---\n{op['plain_text'][:600]}\n\n"
...
"content": ("For each opinion header (--- OPINION N ---), extract: "
            "case_name, citation (docket), court, date_filed. ..."
            f"{headers_text}"),
```

`plain_text` is the full text of a **published Florida court opinion** fetched from the Orin box's `opinions` table (`:265-274`) — public record, not user data. The user's situation tags influence *which* opinions are fetched (ILIKE clauses, `:252-263`) but the tags themselves are **not** in the DeepSeek prompt. This call-site processes zero user PII and zero user legal narrative; the only privacy angle is inferential (the set of opinions weakly reflects the user's issue tags — and DeepSeek can't see even the tags, only 10 opinion headers).

### 3.3 Provider, model, missing-key behavior

Same endpoint, model `"deepseek-chat"`, `max_tokens: 800`, `temperature: 0`, `timeout=15`, via `requests` (`:171-194`). Missing key → **regex fallback** (`:157-162`, `_extract_metadata_regex`, ~60% accuracy per module docstring `:15-16`); API failure → same regex fallback (`:209-216`). Never raises.

### 3.4 Retention

DeepSeek's response (case_name/citation/court/date_filed) is merged into the in-memory opinion dicts (`:200-207`) and returned up through `get_relevant_opinions` into the same SSE `relevant_opinions` event as call-site 1. No DB write, no log of prompt content (failure warning at `:210`).

### 3.5 Liveness — **DEAD in prod / LIVE only from Joe's dev box** + SSH context

This path's DB access is `subprocess.run(["ssh", ..., "joe@100.117.93.67", "psql -U joe -d legal_clear ..."])` (`:278-289`) — an SSH session into Joe's personal Orin AGX (Jetson) over its **Tailscale address** (100.64.0.0/10 CGNAT range), running psql over the Unix socket with peer auth (docstring `:8-16`). From Railway this cannot succeed: the container has neither Joe's SSH private key nor Tailscale membership; `BatchMode=yes` + `ConnectTimeout=5` makes it fail fast and return `[]` (`:290-292`, plus `FileNotFoundError` handling at `:340-342` if `ssh` isn't installed). Since `_batch_extract_metadata` runs only after a successful psql round-trip, **the DeepSeek call at this site is unreachable from production**. It is live from Joe's dev machine, where both the SSH access and `DEEPSEEK_API_KEY` (local `backend/.env:18`) exist. This matches audit open question 9 (keep-or-remove the Orin fallback). Governance note: even dev-only, it moves *public* opinion text through DeepSeek — the disclosure question here is about the processor registry (SPEC_LEDGER gap flagged in DECISIONS.md), not user consent.

## 4. Disclosure inventory — verbatim

Searched: `docs/TERMS_OF_SERVICE.md`, `README.md`, `CLAUDE.md`, entire `frontend/src` (case-insensitive `deepseek|third.party|third parties`).

- `docs/TERMS_OF_SERVICE.md:66-68` (the only third-party-processor disclosure in the product):
  > ## 7. Third-Party Services
  >
  > LegalClear integrates with third-party services, including Stripe (payment processing), Supabase (data storage), and Anthropic (AI model provider). LegalClear is not responsible for the availability, accuracy, or practices of these third-party services. Your use of third-party services is subject to their respective terms.
- `docs/TERMS_OF_SERVICE.md:27` discloses AI use generically ("LegalClear uses artificial intelligence, including large language models…") without naming providers.
- **DeepSeek appears nowhere** in the ToS, README.md, CLAUDE.md, or any frontend source string (zero grep hits in `frontend/src`).
- `backend/.env.example` (26 lines) does **not** list `DEEPSEEK_API_KEY`.

Conclusion: if the DeepSeek paths are kept in any live form, ToS §7 is currently **inaccurate by omission** — it enumerates providers and omits one that (path 1, and path 2 under fallback conditions) processes user legal content.

## 5. Verified vs. inferred vs. UNVERIFIED

**Verified from repo (file:line cited above):** all three prompt constructions and exact payloads; model/endpoint strings; missing-key behavior (silent skip / regex fallback / Anthropic-first ordering); absence of server-side persistence of DeepSeek output; persistence of the intake conversation in `user_profiles`/`attorney_inquiries`; absence of any DeepSeek/third-party disclosure in ToS, README, CLAUDE.md, frontend; absence of `DEEPSEEK_API_KEY` from `.env.example`; presence of `DEEPSEEK_API_KEY` in local `backend/.env` (name only); the criminal path's empty `ctx`.

**Inferred (high confidence, not provable from repo):** police-report findings can embed names/PII from the uploaded report (depends on Claude's Stage-1 output per document); Railway cannot SSH to 100.117.93.67 (no key/Tailscale in the container — standard Railway; the repo's Nixpacks config installs no ssh key); Anthropic key is set in prod (the whole product requires it), making call-site 2 fallback-only.

**UNVERIFIED (blocks final liveness verdicts — needs one Railway lookup):**
1. Is `DEEPSEEK_API_KEY` set in Railway `zesty-delight`? Yes → call-site 1 is LIVE on every prod police-report analysis and call-site 2 is armed for Anthropic outages. No → all three paths are inert in prod and this is a dev-only + latent-code issue.
2. DeepSeek's actual retention/training policy for API traffic (external legal question, not answerable from this repo).
3. Whether `ssh` is even present in the Railway image (affects only *which* way call-site 3 fails; outcome `[]` either way).

## 6. Decision inputs for Joe (per DECISIONS.md Group A #5 — no recommendation enacted, no code changed)

- The three call-sites are **not equivalent**: #2 (intake fallback) sends verbatim name/email/phone + narrative; #1 sends synthesized legal findings from the user's police report; #3 sends only public court text and is unreachable from prod.
- All three degrade gracefully with the key absent — removing/unsetting the key is a zero-crash kill switch (quality cost: generic attorney prompts, regex metadata, Haiku-only intake with FL Bar phone fallback).
- If keeping any path: ToS §7 needs DeepSeek added; SPEC_LEDGER needs the provider registry entry (DECISIONS.md flags this as S1-adjacent); `.env.example` needs the var; and per FOLLOW_UPS.md, S1-3b scheduling waits on this decision.
