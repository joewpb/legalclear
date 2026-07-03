#!/usr/bin/env python3
"""
Step 3: Write 759 legal opinions to Supabase (legal_opinions table).
Upsert batches of 100. Checkpoint after every batch. Resume from checkpoint.
"""

import json, os, sys, time, requests
from datetime import datetime, timezone

# Load creds from legalclear backend .env
env_path = os.path.expanduser("/home/hermes/workspace/legalclear/backend/.env")
url = key = ""
for line in open(env_path):
    line = line.strip()
    if line.startswith("SUPABASE_URL="): url = line.split("=", 1)[1]
    if line.startswith("SUPABASE_SERVICE_KEY="): key = line.split("=", 1)[1]

if not url or not key:
    print("FATAL: Could not load Supabase credentials")
    sys.exit(1)

REST_URL = f"{url}/rest/v1"
TABLE = "legal_opinions"
HEADERS = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

PROC = "/home/hermes/legal_data/processed"
CP_PATH = "/home/hermes/legal_data/write_checkpoint.json"
ERR_LOG = "/home/hermes/legal_data/write_errors.log"

def load_checkpoint():
    if os.path.exists(CP_PATH):
        with open(CP_PATH) as f:
            return json.load(f)
    return {"batches_written": 0, "records_written": 0, "last_cluster_id": None, "failed_cluster_ids": []}

def save_checkpoint(cp):
    cp["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CP_PATH, "w") as f:
        json.dump(cp, f, indent=2)

def log_error(msg):
    with open(ERR_LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")

def flatten_record(d):
    """Map processed JSON to legal_opinions row."""
    p1 = d.get("pass1", {})
    p2 = d.get("pass2", {})
    return {
        "cluster_id": d["cluster_id"],
        "case_name": d.get("case_name", ""),
        "court": d.get("court", ""),
        "date_filed": d.get("date_filed", None),
        "cite_count": d.get("cite_count", 0),
        "parties": p1.get("parties", []),
        "core_facts": p1.get("core_facts", ""),
        "legal_issue": p1.get("legal_issue", ""),
        "holding_raw": p1.get("holding_raw", ""),
        "outcome": p1.get("outcome", ""),
        "key_statutes": p1.get("key_statutes", []),
        "situation_tags": p1.get("situation_tags", []),
        "citation": p1.get("citation", ""),
        "summary_legal": p2.get("summary_legal", ""),
        "summary_plain": p2.get("summary_plain", ""),
        "attorney_prompt": p2.get("attorney_prompt", ""),
        "quality_flagged": d.get("quality_flagged", False),
        "quality_notes": d.get("quality_notes", "")
    }

def upsert_batch(records, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.post(
                f"{REST_URL}/{TABLE}?on_conflict=cluster_id",
                headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                json=records,
                timeout=60
            )
            if resp.status_code in (200, 201):
                return True
            elif resp.status_code == 409:
                # Conflict - try without merge resolution
                resp2 = requests.post(
                    f"{REST_URL}/{TABLE}",
                    headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                    json=records,
                    timeout=60
                )
                return resp2.status_code in (200, 201)
            else:
                log_error(f"HTTP {resp.status_code}: {resp.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                return False
        except Exception as e:
            log_error(f"Exception: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            return False
    return False

def main():
    cp = load_checkpoint()
    print(f"Checkpoint: {cp['records_written']} written, {cp['batches_written']} batches")
    
    # Load all files sorted
    files = sorted(os.listdir(PROC))
    if len(files) != 759:
        print(f"WARNING: Expected 759 files, found {len(files)}")
    
    # Build records, skip already written
    all_records = []
    for fname in files:
        if not fname.endswith(".json"): continue
        cid = int(fname.replace(".json",""))
        if cp.get("last_cluster_id") and cid <= cp["last_cluster_id"]:
            if cid in cp.get("failed_cluster_ids", []):
                all_records.append((cid, json.load(open(f"{PROC}/{fname}"))))
            continue
        all_records.append((cid, json.load(open(f"{PROC}/{fname}"))))
    
    if not all_records:
        # Check if all were already written
        remaining = [f for f in files if f.endswith(".json")]
        remaining_ids = set(int(f.replace(".json","")) for f in remaining)
        written = set(cp.get("failed_cluster_ids", [])) | {int(f.replace(".json","")) for f in files if int(f.replace(".json","")) <= (cp.get("last_cluster_id") or 0)}
        new_records = [(cid, json.load(open(f"{PROC}/{cid}.json"))) for cid in (remaining_ids - written) if cid not in cp.get("failed_cluster_ids", [])]
        all_records = new_records
    
    total = len(all_records)
    print(f"Records to write: {total}")
    
    if total == 0:
        # All done - verify
        print("No records to write. Running verification...")
        # Count in DB
        resp = requests.get(f"{REST_URL}/{TABLE}?select=count", headers=HEADERS)
        print(f"DB count: {resp.text}")
        return
    
    BATCH_SIZE = 100
    batch_num = cp["batches_written"]
    written_total = cp["records_written"]
    last_progress = time.time()
    
    for i in range(0, total, BATCH_SIZE):
        batch = all_records[i:i+BATCH_SIZE]
        batch_num += 1
        
        records = [flatten_record(r[1]) for r in batch]
        cids = [r[0] for r in batch]
        
        success = upsert_batch(records)
        
        if success:
            written_total += len(batch)
            cp["batches_written"] = batch_num
            cp["records_written"] = written_total
            cp["last_cluster_id"] = cids[-1]
        else:
            log_error(f"Batch {batch_num} FAILED after retries: clusters {cids}")
            cp["failed_cluster_ids"] = list(set(cp.get("failed_cluster_ids", []) + cids))
            # Continue anyway per spec
        
        save_checkpoint(cp)
        
        # Progress report
        now = time.time()
        if now - last_progress > 1800 or batch_num % 3 == 0:
            elapsed = now - last_progress if last_progress else 1
            rate = written_total / (elapsed / 60) if elapsed > 0 else 0
            print(f"  Progress: {written_total}/{total} records ({batch_num} batches) | {rate:.0f}/min")
            last_progress = now
        
        # Brief delay
        time.sleep(0.5)
    
    print(f"\nWrite complete. Records: {written_total}")
    print(f"Failed cluster IDs: {cp.get('failed_cluster_ids', [])}")

if __name__ == "__main__":
    main()
