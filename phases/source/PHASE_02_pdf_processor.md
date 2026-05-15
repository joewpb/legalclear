# PHASE 02 — PDF Processing Pipeline
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/services/pdf_processor.py`
- Text extraction from uploaded PDFs (PyMuPDF / pdfplumber)
- OCR fallback (Tesseract) for scanned documents
- Returns `DocumentExtraction` dict: `{text, pages, metadata}`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/services/pdf_processor.py && echo "pdf_processor ok"
grep -E "def extract|PyMuPDF|pdfplumber|tesseract" backend/src/services/pdf_processor.py && echo "extraction methods ok"
uv pip list | grep -Ei "pymupdf|pdfplumber|pytesseract" && echo "deps ok"
```

## Contract provided to later phases

- Used by:
  - Classifier (Phase 03)
  - Explainer (Phase 04)
  - Risk Scanner (Phase 06)
  - Police Report Analyzer (Phase 21 — new)
- Phase 21 reuses this pipeline for multi-document upload.

## What to do if verification fails

STOP. Report which deps are missing. Do NOT install via pip — use `uv add [pkg]` if needed, but only after confirming with the maintainer.

## Final line

```
PHASE 02 VERIFIED — proceed to PHASE 03
```
