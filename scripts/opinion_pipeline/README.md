# Opinion Ingestion Pipeline

5-gate checkpoint discipline for CourtListener FL opinion ingestion into
Supabase (`miedifclpqewnixxkahs.legal_opinions`).

Completed run: 759 Florida opinions processed and written to Supabase,
verified 759/759.

## Gate 1 — DOWNLOAD

```
01_filter/filter_fl_clusters.py
02_paginate/paginate.py
03_extract/extract_opinions.py
03_extract/test_opinions_stream.py
```

CourtListener bulk CSV → filter for FL opinions meeting Phase 1A criteria →
download opinions via pagination → staging/ (raw JSON with opinion_text,
court_id, metadata).

## Gate 2 — PROCESS

```
04_pipeline/batch_pipeline.py
04_pipeline/test_api.py
```

staging/ → LLM Pass 1 (legal extraction: case metadata, parties, statutes,
situation tags) + Pass 2 (plain-language summary: WHAT HAPPENED / THE RULE /
WHAT THE COURT DECIDED / WHY THIS MAY MATTER TO YOU, plus attorney prompt) →
processed/

## Gate 3 — FIX

```
05_fix/fix_summary_plain.py
05_fix/fix_array_fields.py
```

Quality fixes: summary_plain dict→labeled string format (286 records), array
field coercion for Supabase compatibility.

## Gate 4 — RECOVER

```
06_recover/recover_and_retag.py
06_recover/recover_v2.py
```

Failed-cluster recovery: 42 re-tagged, 20 recovered with larger max_tokens.

## Gate 5 — REGENERATE

```
07_regenerate/regenerate_p2.py
07_regenerate/debug_failure.py
```

Targeted Pass 2 regeneration for records that failed validation.

## Gate 6 — VALIDATE

```
08_validate/validate_all.py
```

Full validation of all 759 records:
- cluster_id present, integer
- case_name present, non-empty
- summary_plain ≥ 200 chars, contains all 4 labels
- situation_tags non-empty array
- attorney_prompt present, non-empty

## Gate 7 — WRITE

```
09_write/write_to_supabase.py
```

Upsert to Supabase legal_opinions table on cluster_id conflict. Batches of
100, checkpoint per batch, 3x retry with 2s/4s/8s backoff. Service role key
required (SUPABASE_URL, SUPABASE_SERVICE_KEY env vars).

## Data

- `data/` — staging and processed JSONs (gitignored, .gitkeep only)
- `logs/` — checkpoints, error logs (gitignored, .gitkeep only)

## Requirements

```
openai
httpx
python-dotenv
```
