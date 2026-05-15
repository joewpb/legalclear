# PHASE 03 — Classifier Agent
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/agents/classifier.py`
- Anthropic Claude call with cached system prompt (`cache_control: ephemeral`)
- Classifies legal documents into: `contract`, `lease`, `summons`, `court_order`, `citation`, `police_report`, `immigration_doc`, `other`
- Returns: `{document_type, confidence, jurisdiction_detected}`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/agents/classifier.py && echo "classifier present"
grep -E "def classify_document|cache_control" backend/src/agents/classifier.py && echo "classifier API ok"
grep -E "claude-sonnet-4-6" backend/src/agents/classifier.py && echo "correct model ok"
```

## Contract provided to later phases

- Called by `/api/upload` endpoint (Phase 10)
- Returns structured JSON — strip markdown fences before parsing.
- New Phase 21 (Police Report Analyzer) uses the SAME pattern but its own dedicated agent — does NOT modify this classifier.

## What to do if verification fails

STOP. Classifier is upstream of explainer/risk_scanner/form_guide. If missing, those downstream features can't be assumed to work.

## Final line

```
PHASE 03 VERIFIED — proceed to PHASE 04
```
