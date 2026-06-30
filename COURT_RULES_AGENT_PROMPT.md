# Court Rules Ingest — Agent Prompt

## Context

LegalClear is a Florida legal-information platform. The `court_rules` table is empty. We need to download the official Florida court rules PDFs from flcourts.gov (browser-only — robots.txt prohibits automation), extract the rules from the PDFs, and insert them into the `court_rules` table in Supabase.

## Step 1 — Download the PDFs

Open each URL in a **browser** (not a script — flcourts.gov CDN blocks automated requests). Download the current rules PDF from each page:

| # | Rule Set | Citation Prefix | URL |
|---|----------|----------------|-----|
| 1 | Florida Rules of Civil Procedure | `Fla. R. Civ. P.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-Civil-Procedure |
| 2 | Florida Family Law Rules of Procedure | `Fla. Fam. L. R. P.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Family-Law-Rules-of-Procedure |
| 3 | Florida Small Claims Rules | `Fla. Sm. Cl. R.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Small-Claims-Rules |
| 4 | Florida Probate Rules | `Fla. Prob. R.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Probate-Rules |
| 5 | Florida Rules of General Practice & Judicial Administration | `Fla. R. Gen. Prac. & Jud. Admin.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-General-Practice-and-Judicial-Administration |
| 6 | Florida Rules of Appellate Procedure | `Fla. R. App. P.` | https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-Appellate-Procedure |

**Priority:** #5 (contains Rule 2.514 — computation of time, and Rule 2.516 — service), #1 (civil procedure), #3 (small claims). Do these first if limited on time.

Save the PDFs to `backend/src/data/rules/` as:
- `civil_procedure.pdf`
- `family_law.pdf`
- `small_claims.pdf`
- `probate.pdf`
- `general_practice.pdf`
- `appellate.pdf`

## Step 2 — Extract Rules from PDFs

For each PDF, extract individual rules. A rule typically looks like:

```
RULE 1.140. DEFENSES
(a) When Presented. ...
(b) How Presented. ...
```

Each rule has:
- A **rule number** (e.g., `1.140`)
- A **title** (e.g., `DEFENSES`)
- **Body text** with optional subsections
- May have **committee notes** at the end

Use this logic:
1. Extract plain text from the PDF (PyMuPDF / pdfplumber)
2. Split into individual rules using regex: rules typically start with `RULE` followed by a number
3. For each rule, capture the rule number, title, and full text
4. If committee notes exist, append them to the text

**Sanitize before inserting:** strip NULL bytes (`\x00`) and control characters.

## Step 3 — Insert into Supabase

The `court_rules` table schema (use the Supabase client with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`):

```
citation         TEXT    — e.g., "Fla. R. Civ. P. 1.140"
rule_set         TEXT    — e.g., "civil_procedure", "family_law", "small_claims", "probate", "general_practice", "appellate"
rule_number      TEXT    — e.g., "1.140"
subsection       TEXT    — optional, e.g., "a"
title            TEXT    — e.g., "DEFENSES"
text             TEXT    — full rule text including subsections and notes
effective_date   TEXT    — if found in the PDF
source_url       TEXT    — the flcourts.gov page URL
jurisdiction     TEXT    — always "FL"
```

Upsert on `citation` to avoid duplicates. Insert in batches of 50.

## Step 4 — Verify

Run from `~/legalclear/backend/`:

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']
supabase = create_client(url, key)

r = supabase.table('court_rules').select('count', count='exact').execute()
print(f'court_rules: {r.count} rows')

# Verify key lookups
for cite in ['Fla. R. Civ. P. 1.140', 'Fla. R. Gen. Prac. & Jud. Admin. 2.514', 'Fla. Sm. Cl. R. 7.010']:
    r = supabase.table('court_rules').select('citation').eq('citation', cite).execute()
    status = '✓' if r.data else '✗ NOT FOUND'
    print(f'  {status} {cite}')
"
```

## Notes

- **The `backend/.env` file** has the Supabase credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`). Load them with `load_dotenv()`.
- **Use `uv`** for Python — no pip.
- **No fabricated rules.** If a PDF can't be parsed, skip it and report which one.
- The backend is on port **8001** — don't change it.
- After insert, the `/api/law/rules` endpoint (in `backend/src/api/routers/law.py`) will serve these rules.
