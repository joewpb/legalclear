# Forms Catalog Cleanup — Multi-Phase Build Plan

**Goal:** LegalClear's `court_forms` table must contain ONLY forms a pro se
litigant needs to FILE a court case. Payment forms, financial transaction
forms, and other clerk's-office administrative forms get moved out of the
filing catalog. Every remaining form must be categorized so it surfaces in
the correct LegalClear area. Pro se filing forms stay on our site.

**Hard rules:**
- One phase per agent run. Print `PHASE N COMPLETE` only when the phase's
  Definition of Done passes with real tool output. Never auto-advance.
- Legal data accuracy is paramount — a form in the wrong category misleads
  a pro se user. Any doubt → category `review` + `review_reason`.
- No new tables unless the phase says so. All work in Supabase project
  `miedifclpqewnixxkahs`, table `court_forms`.
- Report by artifact: CSV/JSON output + row counts, never narration.

---

## Phase 1 — Audit and classify (read-only)

**Deliverable:** `forms_audit.csv` with one row per form (all 764) and a
proposed `target_area` for each, plus counts.

1. Query all 764 rows from `court_forms` (Supabase REST or local backend
   DatabaseManager). Include: form_number, title, category, status,
   plain_language_summary, source_page_url.
2. Classify each form into EXACTLY one of:

| target_area | Rule |
|-------------|------|
| `filing` | A form you file with the court to start/respond/advance a case (petition, complaint, motion, answer, notice, affidavit, order to submit) |
| `payment` | Credit card payment forms, fine payment, payment plan, tax deed surplus claims, fee-related clerk forms |
| `redaction` | SSN/bank account redaction request forms (supporting, not case-filing) |
| `uncertain` | Can't determine from title/summary — goes to review |

3. Write `forms_audit.csv` to `scripts/` with columns:
   `id, form_number, title, current_category, current_status, target_area, confidence(high|low), reason`
4. Print counts per target_area and a sample of 5 `payment` rows.

**DoD:**
- [ ] CSV has exactly 764 data rows
- [ ] Every row has a target_area
- [ ] `payment` + `redaction` + `uncertain` combined ≥ 12 (the known junk is ~10-15 rows)
- [ ] Counts printed match CSV

**STOP. Joe reviews the CSV before Phase 2.**

---

## Phase 2 — Recategorize in Supabase

**Deliverable:** Database updated. Forms moved out of the filing path.

1. Read the approved `forms_audit.csv`.
2. For each row where `target_area == payment` or `redaction`:
   - `UPDATE court_forms SET category = 'clerk_administrative', status = 'review', review_reason = '<target_area>: moved out of filing catalog' WHERE id = ...`
3. For rows where `target_area == filing` and `status == published`:
   - Do NOT touch. They stay published.
4. For rows where `target_area == uncertain`:
   - `UPDATE ... SET status = 'review', review_reason = 'form audit: category uncertain'`
5. Print: rows moved to clerk_administrative, rows sent to review, published count before/after.

**DoD:**
- [ ] Zero published forms remain in category `clerk_administrative`
- [ ] Published count printed matches expected (509 minus moved rows)
- [ ] Every moved row has a non-empty review_reason

**STOP. Joe verifies counts.**

---

## Phase 3 — Route forms to the correct LegalClear areas

**Goal:** Every published form must be reachable from the LegalClear feature
where a pro se user would look for it.

1. Read the full published list (post-Phase-2).
2. Build the mapping from `category` → LegalClear surface:

| Category | Where it must surface |
|----------|----------------------|
| `small_claims` | Small Claims wizard (/small-claims/file) — form list step |
| `eviction` | Eviction defense flow (/landlord) |
| `family_law_*`, `domestic_violence`, `name_change` | Family law section + forms finder |
| `probate_estate`, `guardianship` | Wills & Trusts / Probate explainer |
| `county_local`, `circuit_specific` | Forms finder (/forms) with county filter |
| `criminal`, `traffic` | Traffic wizard + criminal explainer |
| `clerk_administrative` | NOT surfaced anywhere in filing flows |

3. Fix the forms finder query (frontend `FormsFinderFL`) so it:
   - Never returns `clerk_administrative` rows
   - Filters by category param where the caller passes one
4. Check each LegalClear surface's form query actually pulls its category.
   Fix any surface that queries `court_forms` without a category filter.
5. `npm run build` — must pass.

**DoD:**
- [ ] `clerk_administrative` excluded from every forms query (grep proof)
- [ ] Forms finder shows county filter for county_local rows
- [ ] Build passes with real output
- [ ] API returns zero clerk_administrative forms on the public forms endpoint

**STOP. Joe clicks through the site.**

---

## Phase 4 — Recover the 218 rejected forms

**Context:** 218 rows are `status=rejected`, mostly "extracted text is empty".
Source PDFs live on the VPS at `/home/hermes/workspace/legal-clear/`
(716 PDFs). Many are recoverable.

1. List the 218 rejected rows. For each, check if a matching PDF exists
   on the VPS (match by form_number or bucket_path hint).
2. For rows WITH a source PDF: re-extract text with pymupdf
   (`fitz`). If extraction yields >100 chars, write `form_text`,
   `plain_language_summary` via DeepSeek (cheap model), set
   `status='published'`.
3. For rows WITHOUT a source PDF: set `review_reason='no source PDF available'`, keep rejected.
4. Print: attempted / recovered / still-rejected counts, with a CSV of recovered rows.

**DoD:**
- [ ] Recovery CSV saved to scripts/
- [ ] ≥ 60% of attempted rows recovered (target — verify against actual extraction)
- [ ] Every recovered row has form_text AND plain_language_summary populated
- [ ] Still-rejected rows all carry a review_reason

**STOP. Joe reviews recovery CSV.**

---

## Phase 5 — Final verification and report

1. Print final state:
   - Total rows, published, review, rejected, stale
   - Published by category (table)
   - Zero `clerk_administrative` rows with status published
2. Random-sample 10 published forms: verify category matches title and
   summary (no financial forms in filing categories).
3. Verify /forms endpoint returns only filing-relevant categories.
4. Commit any code changes from Phase 3. Push main. Empty commit if needed
   to trigger Railway redeploy.

**DoD:**
- [ ] Final state table printed (real query output)
- [ ] 10/10 sample forms have correct category
- [ ] All phases' artifacts present in repo (forms_audit.csv, recovery CSV)
- [ ] Site live with updated catalog

**PROJECT COMPLETE.**
