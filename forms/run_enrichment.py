#!/usr/bin/env python3
"""Phase 10 — enrichment runner (DeepSeek).

Reads forms/enrichment_input.jsonl, generates plain-language summary + situation
tags per form, writes forms/enrichment_output.jsonl. UPL-walled: produces legal
INFORMATION (what a form is / who files it / when), never legal advice.

Run from repo root:
    export DEEPSEEK_API_KEY=sk-...
    python forms/run_enrichment.py                 # full run (154 forms, ~1 req/sec)
    python forms/run_enrichment.py --limit 5       # smoke test the first 5
    python forms/run_enrichment.py --resume        # skip ids already in the output file

Pure stdlib — no external deps. Output is line-appended so a crash is resumable.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FORMS_DIR = Path(__file__).resolve().parent
IN_PATH = FORMS_DIR / "enrichment_input.jsonl"
OUT_PATH = FORMS_DIR / "enrichment_output.jsonl"

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-flash"
RATE_LIMIT_S = 1.0          # 1 request / second
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
  (e.g. a court opinion or a multi-form compendium). When false, set
  form_number to the input value, title to null, plain_language_summary to
  null, situation_tags to [], and give a short review_reason.

Do not invent. If you cannot tell what the form is, mark it not usable.
Output JSON only — no markdown, no preamble."""


def render_user_message(entry, text):
    return (
        f"form_number: {entry.get('form_number')}\n"
        f"title: {entry.get('title')}\n"
        f"category: {entry.get('category')}\n\n"
        f"extracted_text:\n{text}"
    )


def call_deepseek(api_key, user_message):
    """POST to DeepSeek; one retry on 429 / 500. Returns parsed model JSON."""
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    last_err = None
    for attempt in range(2):                       # initial try + single retry
        req = urllib.request.Request(
            API_URL, data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except urllib.error.HTTPError as ex:
            last_err = ex
            if ex.code in (429, 500) and attempt == 0:
                time.sleep(5)
                continue
            raise
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as ex:
            last_err = ex
            raise
    raise last_err


def load_done_ids():
    if not OUT_PATH.exists():
        return set()
    done = set()
    for line in OUT_PATH.read_text().splitlines():
        try:
            done.add(json.loads(line)["id"])
        except Exception:
            pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process only the first N entries")
    ap.add_argument("--resume", action="store_true", help="skip ids already in enrichment_output.jsonl")
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.exit("DEEPSEEK_API_KEY not set in environment.")
    if not IN_PATH.exists():
        sys.exit(f"input not found: {IN_PATH} (run scripts/ingest_forms.py first)")

    entries = [json.loads(l) for l in IN_PATH.read_text().splitlines() if l.strip()]
    if args.limit:
        entries = entries[:args.limit]

    done = load_done_ids() if args.resume else set()
    out_mode = "a" if args.resume else "w"

    processed = skipped = errors = 0
    with OUT_PATH.open(out_mode) as out:
        for entry in entries:
            fid, fn = entry.get("id"), entry.get("form_number")

            if args.resume and fid in done:
                print(f"[skip:done]  id={fid} {fn}", file=sys.stderr)
                continue

            text_file = entry.get("text_file")
            if not text_file:
                print(f"[skip:notext] id={fid} {fn} (text_file is null)", file=sys.stderr)
                skipped += 1
                continue
            text_path = FORMS_DIR / text_file
            if not text_path.exists():
                print(f"[skip:missing] id={fid} {fn} ({text_file} not found)", file=sys.stderr)
                skipped += 1
                continue

            text = text_path.read_text(errors="replace")   # no char cap

            try:
                parsed = call_deepseek(api_key, render_user_message(entry, text))
                result = {
                    "id": fid,
                    "form_number": fn,
                    "title": parsed.get("title"),
                    "plain_language_summary": parsed.get("plain_language_summary"),
                    "situation_tags": parsed.get("situation_tags") or [],
                    "usable": bool(parsed.get("usable")),
                    "review_reason": parsed.get("review_reason"),
                }
                print(f"[ok] id={fid} {fn} usable={result['usable']}", file=sys.stderr)
                processed += 1
            except Exception as ex:
                result = {
                    "id": fid,
                    "form_number": fn,
                    "title": None,
                    "plain_language_summary": None,
                    "situation_tags": [],
                    "usable": False,
                    "review_reason": f"runner_error: {type(ex).__name__}: {ex}",
                }
                print(f"[error] id={fid} {fn}: {ex}", file=sys.stderr)
                errors += 1

            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(RATE_LIMIT_S)

    print(f"\ndone. processed={processed} errors={errors} skipped={skipped} "
          f"-> {OUT_PATH.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
