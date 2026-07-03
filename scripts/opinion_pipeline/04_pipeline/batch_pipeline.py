#!/usr/bin/env python3
"""
Batch Pass 1 + Pass 2 pipeline for Phase 1A opinions.
Reads opinion text from staging/, enriches with cluster metadata,
calls DeepSeek API for two-pass extraction, saves results.
"""

import csv
import json
import os
import re
import sys
import time
import requests
from datetime import datetime, timezone

csv.field_size_limit(sys.maxsize)

# --- CONFIG ---
STAGING_DIR = "/home/hermes/legal_data/staging"
OUTPUT_DIR = "/home/hermes/legal_data/processed"
CLUSTER_META_PATH = "/home/hermes/legal_data/filtered_phase1a_clusters.json"
CHECKPOINT_PATH = "/home/hermes/legal_data/pipeline_checkpoint.json"
ERROR_LOG = "/home/hermes/legal_data/pipeline_errors.log"
def load_api_key():
    """Read DeepSeek API key from .env file (terminal-masked in output but readable by code)."""
    env_path = os.path.expanduser("~/.hermes/.env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1]
    return os.environ.get("DEEPSEEK_API_KEY", "")

API_KEY = load_api_key()
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- PROMPTS ---

PASS1_SYSTEM = """You are a legal data extraction AI. Extract structured data from Florida court opinions.
TAGGING RULES:
- Only tag what the court's actual legal ruling addresses
- Do NOT tag incidental facts (e.g. the stop that led to the case — tag what the HOLDING is about)
- If the case is about criminal charges, always include felony OR misdemeanor based on the charge level
- unlawful_search and fourth_amendment only if the search itself was the legal issue before the court
- traffic_stop only if the stop's legality was the issue ruled on
- foreclosure cases: do NOT add landlord_tenant unless a landlord-tenant relationship was the actual legal issue
- When in doubt, fewer tags — precision over recall
Return ONLY valid JSON, nothing else."""

PASS1_USER = """Extract structured data from this Florida court opinion. Return ONLY valid JSON, nothing else.

{{
  "cluster_id": {cluster_id},
  "case_name": "{case_name}",
  "court": "{court}",
  "date_filed": "{date_filed}",
  "citation": <string, e.g. "887 So. 2d 1063">,
  "cite_count": {cite_count},
  "parties": [<plaintiff>, <defendant>],
  "core_facts": <2-3 sentences, what happened, plain language>,
  "legal_issue": <one sentence, the question the court had to answer>,
  "holding_raw": <one paragraph, what the court decided>,
  "outcome": <one of: "Affirmed", "Reversed", "Remanded",
               "Affirmed in part", "Reversed in part",
               "Dismissed", "Other">,
  "key_statutes": [<list of statutes or constitutional provisions cited>],
  "situation_tags": [<pick all that apply from the list below>]
}}

SITUATION TAGS LIST:
traffic_stop, unlawful_search, fourth_amendment, fifth_amendment,
sixth_amendment, criminal_sentencing, drug_trafficking,
mandatory_minimum, single_subject_clause, constitutional_challenge,
felony, misdemeanor, dui, domestic_violence, injunction,
child_custody, child_support, dissolution_of_marriage, eviction,
landlord_tenant, security_deposit, debt_collection, fdcpa,
foreclosure, personal_injury, slip_and_fall, medical_malpractice,
employment, wrongful_termination, wage_theft, discrimination,
civil_rights, excessive_force, police_misconduct, small_claims,
contract_dispute, probate, guardianship, immigration, expungement,
public_defender, speedy_trial, bail, search_warrant, probable_cause

OPINION TEXT:
{opinion_text}"""

PASS2_SYSTEM = """You are a legal plain-language AI for LegalClear, a Florida legal education platform. Regular people with no legal background use this platform to understand their rights.
Using this pre-extracted case data, generate three outputs.
Return ONLY valid JSON, nothing else."""

PASS2_USER = """Using this pre-extracted case data, generate three outputs. Return ONLY valid JSON, nothing else.

{{
  "summary_legal": <3 sentences — precise legal summary for attorneys or researchers. Include court, holding, and outcome.>,

  "summary_plain": <Plain English breakdown structured exactly as:
    WHAT HAPPENED: [2-3 sentences, zero jargon, explain like talking to a friend]
    THE RULE: [One plain sentence stating the legal rule. Then one sentence explaining WHY that rule exists.]
    WHAT THE COURT DECIDED: [What happened as a result. Plain language. Define any legal term used in parentheses immediately after.]
    WHY THIS MAY MATTER TO YOU: [One paragraph. Describe the type of situation this applies to without directing the user. End with: "This is worth discussing with an attorney."]>,

  "attorney_prompt": <One paragraph. Format: "In [case name], the [court] held that [holding in plain language]. If your situation involves [relevant situation in plain language], ask your attorney about [case name] and what it may mean for your case." Never use directive language. Third person framing only. No legal advice.>
}}

PASS 1 OUTPUT:
{pass1_json}"""


# --- HELPERS ---

def call_deepseek(system, user, retries=3):
    """Call DeepSeek API with retry and backoff."""
    for attempt in range(retries):
        try:
            resp = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096
                },
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                wait = min(2 ** attempt * 5, 60)
                print(f"  429: retry in {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  API error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3)
                continue
            print(f"  Exception: {e}")
            return None
    return None


def extract_json(text):
    """Extract JSON from model output, handling markdown fences."""
    if not text:
        return None
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        import re as _re
        match = _re.search(r'\{.*\}', text, _re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {
        "total_processed": 0,
        "pass1_failures": 0,
        "pass2_failures": 0,
        "empty_tags": 0,
        "last_cluster_id": None,
        "completed_ids": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }


def save_checkpoint(cp):
    cp["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(cp, f, indent=2)


def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")


def main():
    cp = load_checkpoint()

    # Load cluster metadata
    with open(CLUSTER_META_PATH) as f:
        meta_data = json.load(f)
    clusters_map = {c["cluster_id"]: c for c in meta_data["clusters"]}

    # Get all staging files, sorted by cluster_id
    all_files = sorted(
        [f for f in os.listdir(STAGING_DIR) if f.endswith(".json")],
        key=lambda x: int(x.replace(".json", ""))
    )

    # Skip already completed
    completed_set = set(cp.get("completed_ids", []))
    remaining = [f for f in all_files if int(f.replace(".json", "")) not in completed_set]

    print(f"Total staging files: {len(all_files)}")
    print(f"Already completed: {len(completed_set)}")
    print(f"Remaining: {len(remaining)}")

    last_report = time.time()
    last_checkpoint = time.time()

    for idx, filename in enumerate(remaining):
        cluster_id = int(filename.replace(".json", ""))
        filepath = os.path.join(STAGING_DIR, filename)

        # Read opinion
        with open(filepath) as f:
            opinion = json.load(f)

        # Enrich with cluster metadata
        meta = clusters_map.get(cluster_id, {})
        case_name = meta.get("case_name", opinion.get("case_name", ""))
        court_name = "Supreme Court of Florida" if meta.get("court_id") == "fla" else "District Court of Appeal of Florida"
        date_filed = meta.get("date_filed", opinion.get("date_filed", ""))
        cite_count = meta.get("citation_count", opinion.get("cite_count", 0))

        # Get clean opinion text (strip XML)
        import re as _re2
        text = opinion.get("opinion_text", "")
        text = _re2.sub(r'<[^>]+>', ' ', text)
        text = _re2.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long (DeepSeek context limit)
        if len(text) > 80000:
            text = text[:80000] + "... [truncated]"

        # --- PASS 1 ---
        pass1_user = PASS1_USER.format(
            cluster_id=cluster_id,
            case_name=case_name.replace('"', "'"),
            court=court_name,
            date_filed=date_filed,
            cite_count=cite_count,
            opinion_text=text
        )

        print(f"\n[{idx+1}/{len(remaining)}] Cluster {cluster_id}: {case_name[:40]}...")

        pass1_raw = call_deepseek(PASS1_SYSTEM, pass1_user)
        if not pass1_raw:
            cp["pass1_failures"] += 1
            log_error(f"Pass 1 API failure: cluster {cluster_id}")
            save_checkpoint(cp)
            continue

        pass1_data = extract_json(pass1_raw)
        if not pass1_data:
            cp["pass1_failures"] += 1
            log_error(f"Pass 1 JSON parse failure: cluster {cluster_id}. Raw: {pass1_raw[:300]}")
            save_checkpoint(cp)
            continue

        # Check for empty tags
        tags = pass1_data.get("situation_tags", [])
        if not tags:
            cp["empty_tags"] += 1
            log_error(f"Empty tags: cluster {cluster_id}")

        # --- PASS 2 ---
        pass2_user = PASS2_USER.format(pass1_json=json.dumps(pass1_data, indent=2))

        pass2_raw = call_deepseek(PASS2_SYSTEM, pass2_user)
        if not pass2_raw:
            cp["pass2_failures"] += 1
            log_error(f"Pass 2 API failure: cluster {cluster_id}")
            save_checkpoint(cp)
            continue

        pass2_data = extract_json(pass2_raw)
        if not pass2_data:
            cp["pass2_failures"] += 1
            log_error(f"Pass 2 JSON parse failure: cluster {cluster_id}. Raw: {pass2_raw[:300]}")
            save_checkpoint(cp)
            continue

        # --- SAVE ---
        output = {
            "cluster_id": cluster_id,
            "case_name": case_name,
            "court": court_name,
            "date_filed": date_filed,
            "cite_count": cite_count,
            "pass1": pass1_data,
            "pass2": pass2_data,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        output_path = os.path.join(OUTPUT_DIR, f"{cluster_id}.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        cp["total_processed"] += 1
        cp["completed_ids"].append(cluster_id)
        cp["last_cluster_id"] = cluster_id

        # Checkpoint every 50
        if cp["total_processed"] % 50 == 0:
            save_checkpoint(cp)
            elapsed = time.time() - last_checkpoint
            rate = 50 / elapsed if elapsed > 0 else 0
            remaining_count = len(remaining) - idx - 1
            eta = remaining_count / rate / 60 if rate > 0 else 0
            print(f"\n  CHECKPOINT: {cp['total_processed']} done | P1 fails: {cp['pass1_failures']} | "
                  f"P2 fails: {cp['pass2_failures']} | empty tags: {cp['empty_tags']} | "
                  f"rate: {rate:.1f}/min | ETA: {eta:.0f} min")
            last_checkpoint = time.time()

        # Progress report every 30 min
        if time.time() - last_report > 1800:
            elapsed_total = time.time() - last_report
            # Calculate rate safely
            started = cp.get('started_at', '')
            if started:
                try:
                    from datetime import datetime as _dt
                    started_dt = _dt.fromisoformat(started.replace('Z', '+00:00'))
                    elapsed_hrs = (datetime.fromisoformat(datetime.now(timezone.utc).isoformat().replace('Z','+00:00')) - started_dt).total_seconds() / 3600
                except:
                    elapsed_hrs = 0.001
            else:
                elapsed_hrs = 0.001
            rate = cp['total_processed'] / elapsed_hrs if elapsed_hrs > 0 else 0
            print(f"\n  PROGRESS: {cp['total_processed']} processed | "
                  f"P1 fails: {cp['pass1_failures']} | P2 fails: {cp['pass2_failures']} | "
                  f"empty tags: {cp['empty_tags']} | "
                  f"{rate:.0f}/hr")
            last_report = time.time()

        # Brief delay to avoid rate limits
        time.sleep(0.5)

    # --- FINAL REPORT ---
    cp["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_checkpoint(cp)

    elapsed_hours = (datetime.fromisoformat(cp["completed_at"].replace("Z","+00:00")) - 
                     datetime.fromisoformat(cp["started_at"].replace("Z","+00:00"))).total_seconds() / 3600

    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"  Total processed: {cp['total_processed']}")
    print(f"  Pass 1 failures: {cp['pass1_failures']}")
    print(f"  Pass 2 failures: {cp['pass2_failures']}")
    print(f"  Empty tags: {cp['empty_tags']}")
    print(f"  Elapsed: {elapsed_hours:.1f} hours")
    print(f"  Output: {OUTPUT_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
