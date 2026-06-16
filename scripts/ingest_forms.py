#!/usr/bin/env python3
"""Phase 10 — deterministic FL court-forms library ingest.

Pipeline (NO LLM here — enrichment is offloaded):
    clean  -> drop test junk, normalize form numbers
    dedupe -> pick canonical per group by precedence; supersede the rest
    gate   -> status 'published' (clean statewide-numbered) | 'review' (everything messy)
    upload -> canonical/kept PDFs to the Supabase 'court-forms' bucket
    load   -> raw extracted text into court_forms.form_text (untrimmed)
    emit   -> forms_to_enrich.json (input for the cheap enrichment agent)
              dedupe_review.csv     (ambiguous groups a human must resolve)
              ingest_report.json    (full plan / audit)

Run from repo root:
    cd backend
    uv run python ../scripts/ingest_forms.py            # dry-run: plan + artifacts, NO network
    uv run python ../scripts/ingest_forms.py --execute  # also upload PDFs + upsert court_forms

Requires backend/.env with SUPABASE_URL + SUPABASE_SERVICE_KEY (only for --execute).
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FORMS_DIR = REPO / "forms"
MANIFEST = FORMS_DIR / "forms_manifest.json"
BUCKET = "court-forms"

OUT_ENRICH = FORMS_DIR / "forms_to_enrich.json"
OUT_ENRICH_JSONL = FORMS_DIR / "enrichment_input.jsonl"
OUT_DEDUPE = FORMS_DIR / "dedupe_review.csv"
OUT_REPORT = FORMS_DIR / "ingest_report.json"

TQ_RANK = {"clean": 2, "ocr_noisy": 1, "empty": 0}


# ── helpers ─────────────────────────────────────────────────────────────────

def load_env():
    env = REPO / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def norm_form_number(raw):
    """Strip whitespace/newlines; collapse internal spaces. Return None if empty."""
    if not raw:
        return None
    n = re.sub(r"\s+", "", str(raw))
    return n or None


def slug(name):
    """Filesystem-safe synthetic key for unnumbered forms."""
    s = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    s = re.sub(r"[^A-Za-z0-9/_().-]+", "_", s).strip("_")
    return s


def is_circuit(pdf_filename):
    return (pdf_filename or "").lower().startswith("circuits/")


def fillable(e):
    return 1 if e.get("pdf_is_fillable") else 0


def title_is_suspect(title):
    if not title:
        return True
    t = title.strip()
    if len(t) < 6:
        return True
    up = t.upper()
    if up.startswith("OF ") or "PROCEDURE – FORMS" in up or "PROCEDURE - FORMS" in up:
        return True
    if t[0] in "•·-–—*":
        return True
    # Number-echo titles: "12.900 B", "12.903 C  1" — the OCR echoed the form
    # number instead of a real title. Strip a leading form number and require
    # real alphabetic content to remain.
    remainder = re.sub(r"^\d+\.\d+", "", t).strip()
    if len(re.sub(r"[^A-Za-z]", "", remainder)) < 4:
        return True
    return False


def assign_key(e):
    """Catalog identity. Circuit-local forms are keyed by PATH (ignoring any
    mis-parsed statewide number — this also separates the regex false positives).
    Numbered statewide forms key by their FL form number. Everything else by slug."""
    pdf = e["pdf_filename"]
    if is_circuit(pdf):
        return slug(pdf)                       # e.g. circuits/circuit10/5-51.0
    fn = norm_form_number(e.get("form_number"))
    if fn:
        return fn                               # e.g. 12.901(b)(1)
    return slug(Path(pdf).name)                 # e.g. eviction_collier_tenant_packet


def canon_tuple(e):
    """Higher is better. (text quality, fillable, statewide-naming, not-mangled, -len)."""
    base = Path(e["pdf_filename"]).name
    statewide = 1 if re.match(r"^\d", base) else 0
    not_mangled = 0 if "__" in base else 1
    return (
        TQ_RANK.get(e.get("text_quality"), 0),
        fillable(e),
        statewide,
        not_mangled,
        -len(base),
    )


def read_text(e):
    txt = e.get("txt_filename")
    if not txt:
        return ""
    p = FORMS_DIR / txt
    if not p.exists():
        return ""
    try:
        return p.read_text(errors="replace")
    except Exception:
        return ""


# ── pipeline ────────────────────────────────────────────────────────────────

def build_plan():
    manifest = json.loads(MANIFEST.read_text())

    # 1. CLEAN — drop test_685* junk, normalize form numbers in place.
    cleaned, dropped_junk = [], []
    for e in manifest:
        pdf = e.get("pdf_filename") or ""
        if pdf.startswith("test_"):
            dropped_junk.append(pdf)
            continue
        e["form_number"] = norm_form_number(e.get("form_number"))
        e["_key"] = assign_key(e)
        cleaned.append(e)

    # 2. DEDUPE — group by key, pick canonical, supersede the rest.
    groups = defaultdict(list)
    for e in cleaned:
        groups[e["_key"]].append(e)

    rows, ambiguous_groups = [], []
    for key, members in groups.items():
        if len(members) == 1:
            members[0]["_role"] = "canonical"
            rows.append(members[0])
            continue
        ranked = sorted(members, key=canon_tuple, reverse=True)
        if canon_tuple(ranked[0]) == canon_tuple(ranked[1]):
            # cannot break the tie -> do NOT guess
            ambiguous_groups.append((key, members))
            for m in members:
                m["_role"] = "ambiguous"
                rows.append(m)
            continue
        ranked[0]["_role"] = "canonical"
        rows.append(ranked[0])
        for m in ranked[1:]:
            m["_role"] = "superseded"
            rows.append(m)

    # 3. GATE — status + review_reason.
    for e in rows:
        role = e["_role"]
        tq = e.get("text_quality")
        if role == "ambiguous":
            e["_status"], e["_reason"] = "review", "dedupe_ambiguous"
        elif role == "superseded":
            e["_status"], e["_reason"] = "review", "superseded"
        elif tq == "empty":
            e["_status"], e["_reason"] = "review", "failed_extraction"
        elif is_circuit(e["pdf_filename"]):
            e["_status"], e["_reason"] = "review", "circuit_local"
        elif not e.get("form_number"):
            e["_status"], e["_reason"] = "review", "no_form_number"
        elif tq == "ocr_noisy":
            e["_status"], e["_reason"] = "review", "ocr_low_quality"
        elif title_is_suspect(e.get("title")):
            e["_status"], e["_reason"] = "review", "suspect_metadata"
        elif e.get("pdf_pages") and e["pdf_pages"] > 40:
            e["_status"], e["_reason"] = "review", "oversized_suspect_compendium"
        else:
            e["_status"], e["_reason"] = "published", None

    return rows, dropped_junk, ambiguous_groups


def will_persist(e):
    # superseded + ambiguous variants are recorded but never uploaded/inserted.
    return e["_role"] == "canonical"


# ── execution ───────────────────────────────────────────────────────────────

def execute(persist_rows, client):
    uploaded = inserted = failed = 0
    for e in persist_rows:
        key = e["_key"]
        pdf_path = FORMS_DIR / e["pdf_filename"]
        if not pdf_path.exists():
            print(f"  ! missing PDF, skipped: {e['pdf_filename']}")
            failed += 1
            continue
        data = pdf_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        object_path = f"{key}/{pdf_path.name}"
        try:
            client.storage.from_(BUCKET).upload(
                object_path, data,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
            uploaded += 1
        except Exception as ex:
            print(f"  ! upload failed {key}: {ex}")
            failed += 1
            continue

        record = {
            "form_number": key,
            "title": (e.get("title") or key)[:500],
            "category": e.get("category") or "uncategorized",
            "court_revision_date": e.get("revision_date"),
            "form_text": read_text(e),
            "bucket_path": object_path,
            "content_hash": sha,
            "status": e["_status"],
            "review_reason": e["_reason"],
            "last_changed_at": "now()",
            "updated_at": "now()",
        }
        try:
            client.table("court_forms").upsert(
                record, on_conflict="form_number"
            ).execute()
            inserted += 1
        except Exception as ex:
            print(f"  ! db upsert failed {key}: {ex}")
            failed += 1
    return uploaded, inserted, failed


def write_artifacts(rows, dropped_junk, ambiguous_groups):
    persist = [e for e in rows if will_persist(e)]

    # forms_to_enrich.json — one entry per persisted form (published + gated).
    enrich = []
    for idx, e in enumerate(persist):
        text = read_text(e)
        enrich.append({
            "id": idx,                                # join key the runner echoes back
            "form_number": e["_key"],
            "title": e.get("title"),
            "needs_title": title_is_suspect(e.get("title")),  # cheap agent should propose one
            "category": e.get("category"),
            "status": e["_status"],
            "review_reason": e["_reason"],
            "char_count": len(text),
            "text_file": e.get("txt_filename"),      # relative to forms/
            "text_excerpt": text[:4000],
        })
    OUT_ENRICH.write_text(json.dumps(enrich, indent=2, ensure_ascii=False))

    # enrichment_input.jsonl — one object per line, no text_excerpt
    # (the runner reads full text from text_file directly).
    with OUT_ENRICH_JSONL.open("w") as f:
        for e in enrich:
            line = {k: v for k, v in e.items() if k != "text_excerpt"}
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    # dedupe_review.csv — ambiguous groups for a human.
    with OUT_DEDUPE.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "pdf_filename", "text_quality", "pdf_is_fillable", "pdf_pages", "title"])
        for key, members in ambiguous_groups:
            for m in members:
                w.writerow([key, m["pdf_filename"], m.get("text_quality"),
                            m.get("pdf_is_fillable"), m.get("pdf_pages"), m.get("title")])

    # ingest_report.json — full audit.
    report = {
        "manifest_entries": None,
        "dropped_test_junk": dropped_junk,
        "ambiguous_groups": [k for k, _ in ambiguous_groups],
        "rows": [
            {"key": e["_key"], "pdf": e["pdf_filename"], "role": e["_role"],
             "status": e["_status"], "reason": e["_reason"]}
            for e in rows
        ],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return persist


def summarize(rows, dropped_junk, ambiguous_groups, persist):
    by_status = defaultdict(int)
    by_reason = defaultdict(int)
    for e in rows:
        by_status[e["_status"]] += 1
        if e["_reason"]:
            by_reason[e["_reason"]] += 1
    print("\n── INGEST PLAN ─────────────────────────────────────────────")
    print(f"manifest rows kept (after dropping {len(dropped_junk)} test junk): {len(rows)}")
    print(f"will persist (canonical):        {len(persist)}")
    print(f"  published (servable):          {by_status['published']}")
    print(f"  review (gated):                {by_status['review']}")
    print(f"ambiguous dedupe groups:         {len(ambiguous_groups)}  -> dedupe_review.csv")
    print("\n  gate reasons:")
    for r, n in sorted(by_reason.items(), key=lambda x: -x[1]):
        print(f"    {r:30s} {n}")
    print("\n  artifacts written:")
    print(f"    {OUT_ENRICH.relative_to(REPO)}  ({len(persist)} forms for enrichment)")
    print(f"    {OUT_ENRICH_JSONL.relative_to(REPO)}  (jsonl, no text_excerpt)")
    print(f"    {OUT_DEDUPE.relative_to(REPO)}")
    print(f"    {OUT_REPORT.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="upload PDFs + upsert court_forms (default: dry-run, artifacts only)")
    args = ap.parse_args()

    if not MANIFEST.exists():
        sys.exit(f"manifest not found: {MANIFEST}")

    rows, dropped_junk, ambiguous_groups = build_plan()
    persist = write_artifacts(rows, dropped_junk, ambiguous_groups)
    summarize(rows, dropped_junk, ambiguous_groups, persist)

    if not args.execute:
        print("\n(dry-run — no network. Re-run with --execute to upload + write DB.)")
        return

    load_env()
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in backend/.env")
    try:
        from supabase import create_client
    except ImportError:
        sys.exit("supabase package missing — run from backend/ via `uv run`.")
    client = create_client(url, key)

    print("\n── EXECUTING (upload + upsert) ─────────────────────────────")
    uploaded, inserted, failed = execute(persist, client)
    print(f"uploaded PDFs: {uploaded}  |  upserted rows: {inserted}  |  failed: {failed}")


if __name__ == "__main__":
    main()
