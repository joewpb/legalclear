#!/usr/bin/env python3
"""Full enrichment pipeline for harvest-imported forms.

Phase 1 — TEXT EXTRACTION (local, fast):
  Download PDFs from Supabase Storage → extract text with pymupdf
  → save .txt files → write form_text to court_forms.

Phase 2 — ENRICHMENT (API, slow ~1 req/sec):
  Call DeepSeek to generate plain_language_summary + situation_tags
  → write back to court_forms → promote usable forms to 'published'.

Usage:
    cd backend
    uv run python ../scripts/enrich_harvest.py --extract              # Phase 1 only
    uv run python ../scripts/enrich_harvest.py --enrich --limit 5     # smoke test
    uv run python ../scripts/enrich_harvest.py --enrich               # full run
    uv run python ../scripts/enrich_harvest.py --extract --enrich     # both phases

Resumable: checkpoint file tracks completed form_numbers.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FORMS_DIR = REPO / "forms"
TEXT_DIR = FORMS_DIR / "text"
ENRICH_INPUT = FORMS_DIR / "enrichment_input_harvest.jsonl"
ENRICH_OUTPUT = FORMS_DIR / "enrichment_output_harvest.jsonl"
CHECKPOINT = FORMS_DIR / ".enrich_checkpoint.json"
BUCKET = "court-forms"

# DeepSeek config
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
RATE_LIMIT_S = 1.0
REQUEST_TIMEOUT_S = 180

SYSTEM_PROMPT = """You are a Florida court-form cataloguer for LegalClear.
You produce neutral catalog metadata that helps self-represented people FIND and
UNDERSTAND a court form. You provide legal INFORMATION, never legal advice: you
describe what a form is, who files it, and when it is used. You never tell a user
what they should do, never predict outcomes, and never interpret a personal
situation.

You are given a form's number, title, category, and full extracted text. Return a
SINGLE JSON object and nothing else, with exactly these fields:

{
  "form_number": "<echoed from input>",
  "title": "<auto-corrected title from form text, or null if the input title is correct>",
  "plain_language_summary": string | null,
  "situation_tags": string[],
  "usable": boolean,
  "review_reason": string | null
}

- form_number: echo the form_number from the input exactly.
- title: the real, descriptive title of the form as derived from the form
  body text. If the input title is already correct, output it unchanged.
  If it is garbled, truncated, or mislabeled, output the corrected title.
  At most 500 characters. Output null only when usable is false.
- plain_language_summary: 2-4 plain-English sentences — what the form is, who
  files it, and when it is used. No advice, no outcomes.
- situation_tags: 3-8 lowercase snake_case keywords a layperson would search
  (e.g. ["divorce","minor_children","petitioner","child_support"]).
- usable: false if the text is empty, garbled, or not actually a fillable form
  (e.g. a budget report, commission agenda, court opinion, or admin document).
  When false, set form_number to the input value, title to null,
  plain_language_summary to null, situation_tags to [], and give a short review_reason.
- review_reason: null if usable=true. Short explanation if usable=false.

Do not invent. If you cannot tell what the form is, mark it not usable.
Output JSON only — no markdown, no preamble."""


def load_env():
    env = REPO / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def get_supabase_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing")
    return create_client(url, key)


def load_checkpoint():
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text()))
    return set()


def save_checkpoint(done):
    CHECKPOINT.write_text(json.dumps(sorted(done)))


# ── Phase 1: Text Extraction ────────────────────────────────────────────────

def extract_phase(client):
    """Download PDFs from Storage, extract text, save .txt, write form_text to DB."""
    print("── PHASE 1: TEXT EXTRACTION ────────────────────────────────────")
    TEXT_DIR.mkdir(exist_ok=True)

    # Get all harvest-imported forms that have a bucket_path but no form_text
    resp = client.table("court_forms").select(
        "form_number,bucket_path,title,category"
    ).eq("review_reason", "harvest_import").execute()

    forms = resp.data or []
    print(f"Harvest forms to process: {len(forms)}")

    extracted = 0
    skipped_no_bucket = 0
    failed = 0

    for row in forms:
        fn = row["form_number"]
        bucket_path = row.get("bucket_path")
        if not bucket_path:
            skipped_no_bucket += 1
            continue

        # Sanitize form_number for filesystem (replace / with _)
        safe_fn = fn.replace("/", "_")
        txt_path = TEXT_DIR / f"{safe_fn}.txt"
        if txt_path.exists():
            # Already extracted — just ensure form_text is set
            text = txt_path.read_text(errors="replace")
            try:
                client.table("court_forms").update(
                    {"form_text": text[:1000000]}
                ).eq("form_number", fn).execute()
                extracted += 1
            except Exception as ex:
                print(f"  ! DB update failed {fn}: {ex}")
                failed += 1
            continue

        # Download PDF from Storage
        try:
            pdf_bytes = client.storage.from_(BUCKET).download(bucket_path)
        except Exception as ex:
            print(f"  ! download failed {fn} ({bucket_path}): {ex}")
            failed += 1
            continue

        # Extract text
        try:
            import pymupdf
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            text = "\n\n".join(pages)
        except Exception as ex:
            print(f"  ! extraction failed {fn}: {ex}")
            failed += 1
            continue

        # Save .txt — create parent dirs (form numbers may contain /)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(text, errors="replace")

        # Write form_text to DB (truncate to 1M chars — Supabase text limit)
        try:
            client.table("court_forms").update(
                {"form_text": text[:1000000]}
            ).eq("form_number", fn).execute()
            extracted += 1
        except Exception as ex:
            print(f"  ! DB update failed {fn}: {ex}")
            failed += 1
            continue

        if extracted % 50 == 0:
            print(f"  ... {extracted}/{len(forms)} extracted")

    print(f"\nExtraction complete: {extracted} ok | {skipped_no_bucket} no-bucket | {failed} failed")
    return extracted


# ── Phase 2: Enrichment ─────────────────────────────────────────────────────

def call_deepseek(api_key, user_message):
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    last_err = None
    for attempt in range(2):
        req = urllib.request.Request(
            DEEPSEEK_URL, data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            choice = payload.get("choices", [{}])[0]
            msg = choice.get("message")
            if msg is None:
                finish = choice.get("finish_reason", "unknown")
                raise ValueError(f"DeepSeek returned null message (finish_reason={finish})")
            content = msg["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except urllib.error.HTTPError as ex:
            last_err = ex
            body_text = ex.read().decode("utf-8", errors="replace")[:500] if ex.fp else "no body"
            print(f"  [HTTP {ex.code}] {body_text}", file=sys.stderr)
            if ex.code in (429, 500) and attempt == 0:
                time.sleep(5)
                continue
            raise
        except Exception as ex:
            last_err = ex
            import traceback
            print(f"  [API exception] {type(ex).__name__}: {ex}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
    raise last_err


def enrich_phase(client, api_key, limit=None):
    """Call DeepSeek for each extracted form, write results to DB."""
    print("── PHASE 2: DEEPSEEK ENRICHMENT ────────────────────────────────")

    # Get forms that have form_text and are in review (harvest_import)
    resp = client.table("court_forms").select(
        "form_number,title,category,form_text,review_reason"
    ).eq("review_reason", "harvest_import").not_.is_("form_text", "null").execute()

    forms = resp.data or []
    print(f"Forms with extracted text: {len(forms)}")

    done = load_checkpoint()
    forms_to_process = [f for f in forms if f["form_number"] not in done]
    if limit:
        forms_to_process = forms_to_process[:limit]

    print(f"To enrich: {len(forms_to_process)} (already done: {len(done)})")

    processed = errors = skipped_no_text = 0
    out_mode = "a" if ENRICH_OUTPUT.exists() else "w"

    with ENRICH_OUTPUT.open(out_mode) as out:
        for idx, row in enumerate(forms_to_process):
            fn = row["form_number"]
            text = row.get("form_text") or ""  # handle None
            if not text:
                print(f"  [skip] {fn}: empty form_text")
                done.add(fn)
                continue

            # Build user message
            user_msg = (
                f"form_number: {fn}\n"
                f"title: {row.get('title', '')}\n"
                f"category: {row.get('category', '')}\n\n"
                f"extracted_text:\n{text[:12000]}"  # cap to avoid token limits
            )

            try:
                parsed = call_deepseek(api_key, user_msg)
                usable = bool(parsed.get("usable"))
                result = {
                    "form_number": fn,
                    "title": parsed.get("title"),
                    "plain_language_summary": parsed.get("plain_language_summary"),
                    "situation_tags": parsed.get("situation_tags") or [],
                    "usable": usable,
                    "review_reason": parsed.get("review_reason"),
                }

                # Write back to court_forms
                update = {
                    "plain_language_summary": result["plain_language_summary"],
                    "situation_tags": result["situation_tags"],
                    "status": "published" if usable else "review",
                    "review_reason": result["review_reason"] if not usable else None,
                }
                if result["title"]:
                    update["title"] = result["title"][:500]

                client.table("court_forms").update(update).eq("form_number", fn).execute()

                status_icon = "✓" if usable else "✗"
                print(f"  [{status_icon}] {fn} {'published' if usable else 'rejected'}: {result.get('review_reason','')[:80]}")
                processed += 1

            except Exception as ex:
                result = {
                    "form_number": fn,
                    "title": None,
                    "plain_language_summary": None,
                    "situation_tags": [],
                    "usable": False,
                    "review_reason": f"runner_error: {type(ex).__name__}: {ex}",
                }
                print(f"  [err] {fn}: {ex}")
                errors += 1

            # Write to output file
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()

            # Checkpoint
            done.add(fn)
            if processed % 10 == 0:
                save_checkpoint(done)

            time.sleep(RATE_LIMIT_S)

    save_checkpoint(done)
    print(f"\nEnrichment complete: {processed} ok | {errors} errors | {skipped_no_text} no-text")
    return processed, errors


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true", help="Phase 1: download + extract text from PDFs")
    ap.add_argument("--enrich", action="store_true", help="Phase 2: DeepSeek enrichment")
    ap.add_argument("--limit", type=int, default=None, help="Limit enrichment to N forms (smoke test)")
    ap.add_argument("--reset-checkpoint", action="store_true", help="Clear checkpoint, re-process all")
    args = ap.parse_args()

    if not args.extract and not args.enrich:
        ap.print_help()
        sys.exit(1)

    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if args.enrich and not api_key:
        sys.exit("DEEPSEEK_API_KEY not set in environment.")

    client = get_supabase_client()

    if args.reset_checkpoint and CHECKPOINT.exists():
        CHECKPOINT.unlink()
        print("Checkpoint reset.")

    if args.extract:
        extract_phase(client)

    if args.enrich:
        enrich_phase(client, api_key, limit=args.limit)


if __name__ == "__main__":
    main()
