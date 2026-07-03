#!/usr/bin/env python3
"""
CourtListener FL opinion pagination — Phase 1A.
Filters: filed_after=2010-01-01, citeCount >= 20, court=fla+fladistctapp
Saves normalized JSON to /home/hermes/legal_data/staging/
"""

import json
import os
import time
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

TOKEN = "cd06fecd35c1d0fad786bfc3d409621dd2ace989"
STAGING_DIR = "/home/hermes/legal_data/staging"
CHECKPOINT_PATH = "/home/hermes/legal_data/checkpoint.json"
ERROR_LOG = "/home/hermes/legal_data/errors.log"
BATCH_LOG = "/home/hermes/legal_data/phase1a_results.json"

os.makedirs(STAGING_DIR, exist_ok=True)

# Rate limiting
REQ_INTERVAL = 1.2  # seconds between requests
last_req_time = 0

def rate_limit():
    global last_req_time
    now = time.time()
    elapsed = now - last_req_time
    if elapsed < REQ_INTERVAL:
        time.sleep(REQ_INTERVAL - elapsed)
    last_req_time = time.time()

def api_get(url, retries=3):
    """Make authenticated GET request with retry & backoff."""
    rate_limit()
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Authorization": f"Token {TOKEN}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code == 429:
                wait = min(2 ** attempt * 5, 30)
                print(f"  429: retry in {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 503:
                wait = min(2 ** attempt * 3, 15)
                print(f"  503: retry in {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  HTTP {e.code}: {body}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            print(f"  Error: {e}")
            return None
    return None

def get_opinion_text(opinion_id):
    """Fetch full opinion text from /opinions/{id}/."""
    url = f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/"
    data = api_get(url)
    if not data:
        return None, None
    text = data.get("html_with_citations") or data.get("plain_text") or ""
    return text, data.get("local_path")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {
        "last_cursor": None,
        "total_processed": 0,
        "total_duplicates": 0,
        "total_errors": 0,
        "total_cited": 0,
        "court_counts": {},
        "last_run_timestamp": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "phase": "phase1a",
        "filter": "filed_after=2010-01-01, citeCount>=20, court=fla+fladistctapp"
    }

def save_checkpoint(cp):
    cp["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(cp, f, indent=2)

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")

def process_opinion(search_result):
    """Extract and save one opinion cluster from search result."""
    cluster_id = search_result["cluster_id"]
    staging_path = os.path.join(STAGING_DIR, f"{cluster_id}.json")

    # Dedup check
    if os.path.exists(staging_path):
        return "duplicate"

    # Get cluster details for precedential_status
    cluster_url = f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/"
    cluster_data = api_get(cluster_url)

    # Get opinion text from first opinion in the cluster
    opinions_list = search_result.get("opinions", [])
    opinion_text = ""
    opinion_id = None
    local_path = None

    for op in opinions_list:
        op_id = op.get("id")
        if op_id:
            opinion_id = op_id
            text, lp = get_opinion_text(op_id)
            if text:
                opinion_text = text
                local_path = lp
            break  # Get text from first opinion only

    # Build normalized record
    record = {
        "cluster_id": cluster_id,
        "case_name": search_result.get("caseName", ""),
        "case_name_full": search_result.get("caseNameFull", ""),
        "court": search_result.get("court", ""),
        "court_id": search_result.get("court_id", ""),
        "court_jurisdiction": search_result.get("court_jurisdiction", ""),
        "date_filed": search_result.get("dateFiled"),
        "date_argued": search_result.get("dateArgued"),
        "citation": search_result.get("citation", []),
        "neutral_cite": search_result.get("neutralCite", ""),
        "lexis_cite": search_result.get("lexisCite", ""),
        "cite_count": search_result.get("citeCount", 0),
        "docket_number": search_result.get("docketNumber", ""),
        "docket_id": search_result.get("docket_id"),
        "absolute_url": search_result.get("absolute_url", ""),
        "status": search_result.get("status", ""),
        "precedential_status": cluster_data.get("precedential_status") if cluster_data else None,
        "source": search_result.get("source", ""),
        "syllabus": search_result.get("syllabus", ""),
        "suit_nature": search_result.get("suitNature", ""),
        "judge": search_result.get("judge", ""),
        "opinion_id": opinion_id,
        "opinion_text": opinion_text,
        "local_path": local_path,
        "opinions_cited": [op.get("cites", []) for op in opinions_list],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "ingest_source": "courtlistener_phase1a"
    }

    with open(staging_path, "w") as f:
        json.dump(record, f, indent=2)

    return "saved"

def main():
    cp = load_checkpoint()
    cp["started_at"] = cp.get("started_at") or datetime.now(timezone.utc).isoformat()

    start_url = (
        "https://www.courtlistener.com/api/rest/v4/search/"
        "?type=o"
        "&court=fla,fladistctapp"
        "&filed_after=2010-01-01"
        "&order_by=citeCount+desc"
        "&page_size=100"
        "&q=citeCount%3A%5B20+TO+*%5D"
    )

    # Resume from checkpoint cursor if available
    if cp.get("last_cursor") and cp["last_cursor"] not in (None, ""):
        next_url = f"https://www.courtlistener.com/api/rest/v4/search/?cursor={cp['last_cursor']}&court=fla,fladistctapp&filed_after=2010-01-01&order_by=citeCount+desc&page_size=100&q=citeCount%3A%5B20+TO+*%5D&stat_Published=on&type=o"
        print(f"Resuming from cursor: {cp['last_cursor'][:40]}...")
        print(f"Already processed: {cp['total_processed']}, duplicates: {cp['total_duplicates']}, errors: {cp['total_errors']}")
    else:
        next_url = start_url
        print(f"Starting fresh from: {start_url}")

    page = 0
    last_progress_time = time.time()
    last_report_time = time.time()

    while next_url:
        page += 1
        print(f"\n--- Page {page} ---")

        data = api_get(next_url)
        if not data:
            print(f"  Failed to fetch page {page}, aborting")
            log_error(f"Failed to fetch page {page}: {next_url}")
            break

        results = data.get("results", [])
        total_count = data.get("count", 0)
        print(f"  Count: {total_count}, Results on page: {len(results)}")

        # Process each result
        for i, r in enumerate(results):
            cluster_id = r.get("cluster_id")
            try:
                outcome = process_opinion(r)
                if outcome == "saved":
                    cp["total_processed"] += 1
                    court_id = r.get("court_id", "unknown")
                    cp["court_counts"][court_id] = cp["court_counts"].get(court_id, 0) + 1
                elif outcome == "duplicate":
                    cp["total_duplicates"] += 1
                else:
                    cp["total_errors"] += 1
                    log_error(f"Unknown outcome for cluster {cluster_id}")
            except Exception as e:
                cp["total_errors"] += 1
                log_error(f"Error processing cluster {cluster_id}: {e}")
                print(f"  ERROR cluster {cluster_id}: {e}")

            # Progress every 50 opinions
            total = cp["total_processed"] + cp["total_duplicates"]
            if total > 0 and total % 50 == 0:
                elapsed = time.time() - last_progress_time
                rate = 50 / elapsed if elapsed > 0 else 0
                remaining = (total_count - total) / rate if rate > 0 else 0
                print(f"  Progress: {cp['total_processed']} saved, {cp['total_duplicates']} dup, "
                      f"{cp['total_errors']} err | {rate:.1f}/min | ~{remaining/60:.0f}min left")
                last_progress_time = time.time()

            # Checkpoint every 100
            if total > 0 and total % 100 == 0:
                cp["last_cursor"] = data.get("next", "")
                save_checkpoint(cp)

        # Update cursor
        next_url = data.get("next")
        if next_url:
            cp["last_cursor"] = next_url
        else:
            cp["last_cursor"] = None

        # Final checkpoint for this page
        save_checkpoint(cp)

    # Done
    print("\n" + "=" * 60)
    print("PHASE 1A COMPLETE")
    print(f"  Opinions saved: {cp['total_processed']}")
    print(f"  Duplicates skipped: {cp['total_duplicates']}")
    print(f"  Errors: {cp['total_errors']}")
    for cid, cnt in sorted(cp["court_counts"].items()):
        print(f"  {cid}: {cnt}")
    print(f"  Staging: {STAGING_DIR}/")
    print("=" * 60)

    cp["last_cursor"] = None
    cp["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_checkpoint(cp)

    # Write final results summary
    with open(BATCH_LOG, "w") as f:
        json.dump(cp, f, indent=2)

if __name__ == "__main__":
    main()
