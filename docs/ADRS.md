# LegalClear — Architecture Decision Records

Written 2026-08-17 (Phase H) against main @ `f145dd8`.

---

## ADR-1 — Case law lookup is deterministic by design

**Status:** ACCEPTED (Joe, recorded 2026-08-13 in `DECISIONS.md`, Decision 2 of the
audit triage).

The following is the ADR text from `DECISIONS.md`, quoted verbatim:

> Case law lookup is deterministic database retrieval, not LLM. legal_opinions holds
> 425,850 Florida opinions. Only 759 rows (0.18%) ever received LLM-generated
> situation_tags, so tag-based retrieval returned empty for most searches. The options
> were to run an LLM over all 425,850 rows (thousands of dollars, weeks of API time) or
> search the already-populated plain-English summary column directly with Postgres ILIKE
> backed by a pg_trgm index — 100% row coverage, instant, zero cost. The deterministic
> path was chosen deliberately.
>
> Citation treatment (4,749 FL cases with negative treatment) is also deterministic:
> parsed from CourtListener's parentheticals bulk CSV with keyword rules, deliberately
> zero AI, because fabricated case citations carry felony-level risk.
>
> This follows the core principle in AGENTS.md: LLMs extract and explain; deterministic
> code computes and retrieves.
>
> LLM is used only in: document intake (classifier/risk_scanner/scanner/explainer),
> Police Report Analyzer, Discovery Motion Analyzer, Criminal Procedure Explainer,
> Property & Casualty Explainer, Small Claims Explainer, Wills & Trusts Explainer,
> Expungement analyzer, Form guidance, Forms /suggest, Attorney Referral intake chat,
> ChatExpert, and opinion-retrieval query synthesis.

**Correction this ADR supersedes.** The stale, LLM-produced claim that case-law
lookup ran on an LLM lived in **`SPEC_LEDGER.md`** (versions dated 2026-06-30
through 2026-08-16, now in git history): the Section 1 ledger row for Case Law
stated the agent was *"none — inline Anthropic call (`case_law.py:72`)"*, and the
Section 4 model-pinning registry listed `routers/case_law.py:72` as a
`claude-sonnet-4-6` call site. At `f145dd8`, `backend/src/api/routers/case_law.py`
contains no LLM call: it ILIKE-searches the scalar text columns of
`legal_opinions` via PostgREST. The rebuilt `SPEC_LEDGER.md` (2026-08-17) records
the deterministic implementation.

**Related disclosure gap, also recorded per `DECISIONS.md`:** at the time of the
decision, `opinion_retrieval.py` and `orin_opinions.py` used **DeepSeek**, and the
SPEC_LEDGER model registry omitted that provider entirely — an S1-adjacent
disclosure problem, not a cosmetic one. That gap was closed by **Decision 7**
(2026-08-15): all three DeepSeek call sites were repointed to Claude Haiku,
enforced by `backend/tests/test_no_deepseek_in_production.py`.

---

## ADR-2 — Uploaded documents are never persisted

**Status:** ACCEPTED (2026-08-17). Non-persistence of originals is retained as the
product's data-minimization posture going forward.

**What the code does (read at `f145dd8`).** `POST /upload` in
`backend/src/api/routes.py` reads the raw request body into memory
(`data = await request.body()`), runs it through `ingest_document()`
(`backend/src/ingestion/`), and persists **only the cleaned extracted text**:
`db.create_document(session_id, doc.get("cleaned_text", ""))` writes
`documents.document_text` via `backend/src/memory/db.py`. The original file bytes
are discarded when the request completes. There is no Supabase Storage write
anywhere in the upload path, and no storage bucket for user uploads exists —
Supabase Storage holds court forms only.

**Was this deliberate minimization or an accident?** Stated plainly: **in origin it
was an accident, not a designed minimization.** No spec, phase document, or
decision record predating the audit chose non-persistence; and the S2-5a defect
showed that for months even the *extracted text* was silently not stored (the 45
legacy documents in prod have empty `document_text`). A designed minimization
policy would not have shipped with a broken text-persistence path and no recorded
rationale.

**Why the status is nonetheless ACCEPTED.** The basis is the recovery evidence in
`FOLLOW_UPS.md` (S2-5 follow-up) and the remediation that followed: when the 45
legacy documents proved unrecoverable (no upload bucket exists; text was never
stored due to S2-5a), the remediation chose to ship a **user-facing empty state
directing re-upload** (night run 2026-08-16, Lane A) rather than to add original
storage. That choice — build the product around non-persistence instead of
reversing it — is the acceptance. It also matches the platform's exposure profile:
uploaded court documents are PII-dense, and not retaining originals bounds the
breach surface of the sole service-role backend.

**Recorded consequence.** A document whose extracted text is empty is
**unreprocessable, permanently**. There is no original to re-OCR or re-parse;
reprocessing is only possible by the user re-uploading the file. Any future
"reprocess" feature requires reversing this ADR first (adding an uploads bucket +
retention policy), not a workaround.

---

## ADR-3 — User-supplied facts never live on pipeline-owned rows

**Status:** ACCEPTED (implemented 2026-08-16, B5-f3/B5-f4; user columns dropped
from prod 2026-08-17, Phase G).

**Context — one design error, four shipped variants (B5-f1..f4).** The
user-supplied service date feature ("I was served on X, by method Y") failed four
times, each failure a different symptom of the same underlying design error:

1. **B5-f1 — the user's date was ignored:** compute used the freshly extracted
   date instead of the user's.
2. **B5-f2 — dead-code ordering:** the anchor gate ("is a user date allowed
   here?") fired **before** the user-supplied record was ever consulted, so the
   consultation path was unreachable.
3. **B5-f3 (symptom) — the method lost:** the user's date won but the freshly
   extracted service *method* won at compute time, so posted-service cases
   computed the wrong deadline variant.
4. **B5-f4 (symptom) — clobbering and duplication:** the user's answers were
   stored as `user_*` columns on `trigger_events` — rows the pipeline rewrites on
   every recompute — so each run wiped the user's facts before reading them, and
   multiple extracted events each got the user's answer applied, producing
   duplicate deadline rows.

**Root rule.** **A user-supplied fact must never share a database row with
anything an automated pipeline rewrites.** If the machine owns the row's
lifecycle, the machine will eventually overwrite, reorder, or out-vote the human
fact — the four variants above are just the four ways that happens.

**Structural fix.**
- `document_service_facts` — a table the pipeline **never writes**
  (`supabase/migrations/20260815000002_b5f3_document_service_facts.sql`). The
  user's date + method live there with `user_supplied` provenance; at compute
  time the record is read once, as a unit, and overrides every extracted value
  (`backend/deadline/pipeline.py`, `backend/src/memory/db.py`).
- **Unconditional dedup on `(document_id, governing_rule)`** — one deadline row
  per legal obligation per document (B5-f4). If two extracted events would yield
  different dates for the same obligation, the pipeline escalates for review
  instead of writing two rows.
- The failed design was removed, not deprecated in place: the
  `get/set_user_supplied_service_date` helpers were deleted and the
  `trigger_events.user_*` columns dropped in prod
  (`supabase/migrations/20260817010000_g_drop_trigger_events_user_columns.sql`).

**Evidence.** `backend/tests/test_deadline_service_date.py` and
`backend/tests/test_anchor_gate.py` (unit), plus the live 4-case gate recorded in
`docs/night-run-2026-08-16-explained.md` §2.4 (personal-service date wins; posted
without mailing date → 422; posted computes later-of; "I don't know" escalates
with zero rows).
