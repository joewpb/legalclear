# LegalClear County Harvest Integration — June 22, 2026

## What We Did

Integrated 610 county-level court forms from the separate harvest repo
(`/home/hermes/workspace/legal-clear/`) into the main LegalClear pipeline
(Supabase + FastAPI). The harvest repo had been scraping county clerk
websites for months but the data was never connected to the production
database.

## Before vs After

| Metric | Before | After |
|--------|--------|-------|
| Forms in `court_forms` table | ~167 | **796** |
| Forms in `forms_manifest.json` | 167 | **777** |
| PDFs in Supabase Storage | ~120 | **684** |
| Published (enriched with summaries) | 58 | **443** |
| Counties covered | 4 of 20 | **41 counties** |
| Circuit-specific forms | 4 circuits | **Same, plus county-local** |

## Where Everything Sits

### Supabase (production database)
- **Project:** `miedifclpqewnixxkahs` (us-west-2)
- **Table:** `court_forms` — 796 rows
  - 443 `published` (enriched with plain-language summaries + situation_tags)
  - 321 `review` (rejected admin docs / pending)
  - 32 `unverified` (original seed)
- **Storage bucket:** `court-forms` — 684 PDFs
  - Original path: `{key}/{filename}` (e.g., `12.901(a)/901a.pdf`)
  - Harvest path: `harvest/{key}/{filename}` (e.g., `harvest/St._Johns/st-johns-Quiet-Title/...pdf`)

### GitHub
- **Repo:** `github.com/joewpb/legalclear`
- **Commit:** `954ed06` — `feat: integrate county harvest forms`
- **Files pushed:**
  - `scripts/bridge_harvest.py` — Step 1: upload + insert
  - `scripts/enrich_harvest.py` — Step 2+3: extract text + DeepSeek enrichment
  - `forms/forms_manifest.json` — expanded 167 → 777 entries
  - `.gitignore` — excludes checkpoint/output/text artifacts

### Pop-OS (`/home/joe/code/legal-clear/`)
- Git repo synced (same as GitHub)
- `forms/` directory contains:
  - `.enrich_checkpoint.json` — 546 form numbers, resumability tracker
  - `enrichment_output_harvest.jsonl` — 558 per-form enrichment results
  - `enrichment_output.json` — original enrichment output
  - `text/` and flat `.txt` files — 560 extracted text files (36MB)

### This Machine (Pop-OS VPS, `/home/hermes/workspace/legalclear/`)
- Working repo with all scripts, manifest, and local artifacts
- `forms/text/` — 560 extracted text files
- `backend/.env` — contains Supabase + DeepSeek credentials (NOT in git)

## Files Created

| File | Purpose |
|------|---------|
| `scripts/bridge_harvest.py` | Reads harvest `forms.jsonl` → maps to pipeline schema → uploads PDFs to Supabase Storage → inserts into `court_forms` → updates `forms_manifest.json` |
| `scripts/enrich_harvest.py` | Phase 1 (`--extract`): Downloads PDFs from Storage, extracts text with pymupdf, writes to `form_text`. Phase 2 (`--enrich`): Calls DeepSeek API to generate `plain_language_summary`, `situation_tags`, auto-corrected `title`, and `usable` verdict. Writes back to `court_forms`. Checkpoint-resumable. |
| `forms/forms_manifest.json` | Expanded from 167 to 777 entries. Each entry: `pdf_filename`, `form_number`, `title`, `category`, `source`, `text_quality`, etc. |

## How to Run Again (for new harvest data)

### Prerequisites
Set credentials in `backend/.env`:
```
SUPABASE_URL=https://miedifclpqewnixxkahs.supabase.co
SUPABASE_SERVICE_KEY=<JWT service-role key>
DEEPSEEK_API_KEY=*** Step 1: Bridge (diff + upload + insert)
```bash
cd /home/hermes/workspace/legalclear/backend
uv run python ../scripts/bridge_harvest.py           # dry-run
uv run python ../scripts/bridge_harvest.py --execute  # upload + insert
```

### Step 2: Extract text from PDFs
```bash
cd /home/hermes/workspace/legalclear/backend
PYTHONUNBUFFERED=1 uv run python ../scripts/enrich_harvest.py --extract
```

### Step 3: Enrich via DeepSeek
```bash
cd /home/hermes/workspace/legalclear/backend
PYTHONUNBUFFERED=1 uv run python ../scripts/enrich_harvest.py --enrich

# Smoke test first:
uv run python ../scripts/enrich_harvest.py --enrich --limit 5 --reset-checkpoint
```

### Step 4: Verify
```python
from supabase import create_client
c = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
resp = c.table('court_forms').select('status').execute()
# Check published vs review vs unverified counts
```

## Pipeline Architecture

```
Harvest Repo                          Main Pipeline
─────────────                         ──────────────
forms.jsonl (697 entries)             forms_manifest.json (777 entries)
raw/forms/*.pdf (610 PDFs)    ──→    Supabase Storage "court-forms" (684 PDFs)
                                     Supabase court_forms table (796 rows)
                                     DeepSeek API → plain_language_summary
                                                   → situation_tags
                                                   → usable (bool)
```

## Key Decisions & Pitfalls

1. **DeepSeek is NOT blocked** — the API works fine for legal text. `NoneType` errors were a parsing bug in the script (fixed by checking `msg is None` before accessing `msg["content"]`).

2. **County scrapes are ~80% non-forms** — budget PDFs, fee schedules, press releases, admin orders. DeepSeek correctly rejects these as `usable=false`. Only ~2-3% are actual fillable court forms.

3. **Form numbers with `/`** — county-local forms use paths like `St._Johns/st-johns-Quiet-Title`. The manifest entries use these as form_numbers. Filesystem paths sanitize `/` to `_`.

4. **Unicode null bytes** — some PDFs have `\u0000` in extracted text. These fail Supabase writes. Strip with `text.replace('\u0000', '')`.

5. **Python stdout buffering** — always use `PYTHONUNBUFFERED=1` for background runs. The enrichment script uses `print(..., file=sys.stderr)` for progress.

6. **Checkpoint mechanism** — `forms/.enrich_checkpoint.json` is a JSON array of completed form_numbers. Delete to re-process all. The enrichment output is append-only to `enrichment_output_harvest.jsonl`.

## Published Court Forms (sample)

13 real county-level court forms were identified and published from the harvest:

| Form | County | What |
|------|--------|------|
| Form 2.603 | Columbia | Notice of Change of Address |
| Traffic Fine Payment | Columbia | Credit card fax form |
| Declaration of Domicile | Duval | Residency declaration |
| Quit-Claim Deed | Duval | Property transfer |
| Subpoena Duces Tecum | Miami-Dade | Trial document subpoena |
| Name/Address Change | Orange | Email designation |
| Change of Address | St. Lucie | FL Form 2.601 |
| Request for Removal | Volusia | Official records redaction |
| Foreclosure Surplus Claim | Walton | Owner surplus claim |
| Replevin Packet | Walton | Personal property recovery |

Plus the original 58 Supreme Court family law forms already in the system.

## Skill

A Hermes skill was created: `legalclear-harvest-integration`
Load with `skill_view(name='legalclear-harvest-integration')` for detailed step-by-step guidance.
