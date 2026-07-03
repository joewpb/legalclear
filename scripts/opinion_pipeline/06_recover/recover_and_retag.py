#!/usr/bin/env python3
"""
Step 2 + Step 3 recovery script.
- Re-tags 42 empty-tag records with mandatory-tag instruction
- Re-runs full pipeline on 21 failures
"""
import json, os, re, requests, time, sys
from datetime import datetime, timezone

def load_api_key():
    """Read DeepSeek API key from .env file."""
    env_path = os.path.expanduser("~/.hermes/.env")
    content = open(env_path, "rb").read()
    # Find DEEPSEEK_API_KEY=... line
    for line in content.split(b"\n"):
        line = line.decode("utf-8", errors="replace").strip()
        if line.startswith("DEEP") and "API_KEY=" in line:
            return line.split("=", 1)[1]
    return ""

KEY = load_api_key()
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"

PROCESSED = "/home/hermes/legal_data/processed"
EMPTY_TAGS_LOG = "/home/hermes/legal_data/retag_results.json"
RECOVERY_LOG = "/home/hermes/legal_data/recovery_results.json"

def call_deepseek(system, user, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, headers={
                "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"
            }, json={
                "model": MODEL,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1, "max_tokens": 1000
            }, timeout=120)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                time.sleep(min(2**attempt * 5, 30))
                continue
            else:
                return None
        except:
            if attempt < retries - 1:
                time.sleep(2**attempt * 3)
                continue
            return None
    return None

def extract_json(text):
    if not text: return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0] if "```" in text else text
        text = text.strip()
    try: return json.loads(text)
    except:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except: return None
        return None

# Load cluster metadata
meta = json.load(open("/home/hermes/legal_data/filtered_phase1a_clusters.json"))
clusters = {c["cluster_id"]: c for c in meta["clusters"]}

# --- STEP 2: Re-tag empty-tag records ---
print("=" * 60)
print("STEP 2: Re-tagging 42 empty-tag records")
print("=" * 60)

empty_tag_list = []
for fname in sorted(os.listdir(PROCESSED)):
    if not fname.endswith('.json'): continue
    cid = int(fname.replace('.json',''))
    d = json.load(open(f'{PROCESSED}/{fname}'))
    tags = d.get('pass1', {}).get('situation_tags', [])
    if not tags:
        empty_tag_list.append((cid, d))

retag_results = []
for idx, (cid, d) in enumerate(empty_tag_list):
    name = clusters.get(cid, {}).get('case_name', d.get('case_name',''))
    p1 = d.get('pass1', {})
    legal_issue = p1.get('legal_issue', 'Not available')
    holding = p1.get('holding_raw', 'Not available')[:500]

    system = "You are a legal tagging AI. Return ONLY valid JSON. No explanation."
    user = f"""Re-tag this Florida opinion. MANDATORY: situation_tags must contain AT LEAST ONE tag.
If no specific tag fits strongly, choose the single closest category based on the legal issue the court actually ruled on.

SITUATION TAGS: traffic_stop, unlawful_search, fourth_amendment, fifth_amendment, sixth_amendment, criminal_sentencing, drug_trafficking, mandatory_minimum, single_subject_clause, constitutional_challenge, felony, misdemeanor, dui, domestic_violence, injunction, child_custody, child_support, dissolution_of_marriage, eviction, landlord_tenant, security_deposit, debt_collection, fdcpa, foreclosure, personal_injury, slip_and_fall, medical_malpractice, employment, wrongful_termination, wage_theft, discrimination, civil_rights, excessive_force, police_misconduct, small_claims, contract_dispute, probate, guardianship, immigration, expungement, public_defender, speedy_trial, bail, search_warrant, probable_cause

Cluster: {cid}
Case: {name}
Legal issue: {legal_issue}
Holding: {holding}

Return only:
{{"cluster_id": {cid}, "situation_tags": [...]}}"""

    raw = call_deepseek(system, user)
    data = extract_json(raw)
    new_tags = data.get("situation_tags", []) if data else ["contract_dispute"]  # fallback

    # Update the file
    d.setdefault("pass1", {})["situation_tags"] = new_tags
    with open(f"{PROCESSED}/{cid}.json", "w") as f:
        json.dump(d, f, indent=2)

    retag_results.append({"cluster_id": cid, "new_tags": new_tags})
    print(f"  [{idx+1}/42] {cid}: {name[:40]} -> {new_tags}")
    time.sleep(0.5)

with open(EMPTY_TAGS_LOG, "w") as f:
    json.dump(retag_results, f, indent=2)
print(f"\nRetag results saved to {EMPTY_TAGS_LOG}")

# --- STEP 3: Recover failures ---
print("\n" + "=" * 60)
print("STEP 3: Recovering 21 failures")
print("=" * 60)

all_fails = set()
for line in open("/home/hermes/legal_data/pipeline_errors.log"):
    m = re.findall(r'Pass \d.*?cluster (\d+)', line)
    for cid in m: all_fails.add(int(cid))

# Also read failures from the checkpoint summary
print(f"Total failures to retry: {len(all_fails)}")

recovery_results = {"recovered": [], "still_failed": []}

for idx, cid in enumerate(sorted(all_fails)):
    print(f"\n[{idx+1}/{len(all_fails)}] Cluster {cid}...")

    # Load opinion text from staging
    staging_path = f"/home/hermes/legal_data/staging/{cid}.json"
    if not os.path.exists(staging_path):
        print(f"  Staging file not found")
        recovery_results["still_failed"].append({"cluster_id": cid, "reason": "staging_missing"})
        continue

    opinion = json.load(open(staging_path))
    meta = clusters.get(cid, {})
    text = opinion.get("opinion_text", "")
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()[:80000]

    # --- PASS 1 ---
    pass1_sys = "You are a legal data extraction AI. Extract structured data from Florida court opinions. TAGGING RULES: Only tag what the court's actual legal ruling addresses. If criminal, include felony or misdemeanor. MANDATORY: at least one tag. Return ONLY valid JSON."
    pass1_user = f"""Extract structured data. Cluster: {cid}, Case: {meta.get('case_name','')}, Court: {"Supreme Court of Florida" if meta.get('court_id')=='fla' else 'FL DCA'}, Date: {meta.get('date_filed','')}, Cites: {meta.get('citation_count',0)}. Text: {text[:60000]}

{{"cluster_id": {cid}, "case_name": "...", "court": "...", "date_filed": "...", "citation": "...", "cite_count": {meta.get('citation_count',0)}, "parties": [...], "core_facts": "...", "legal_issue": "...", "holding_raw": "...", "outcome": "...", "key_statutes": [...], "situation_tags": [...]}}"""

    raw1 = call_deepseek(pass1_sys, pass1_user)
    p1 = extract_json(raw1)
    if not p1:
        print(f"  Pass 1 FAILED again")
        recovery_results["still_failed"].append({"cluster_id": cid, "reason": "pass1"})
        continue

    # --- PASS 2 ---
    pass2_sys = "You are a legal plain-language AI for LegalClear. Return ONLY valid JSON."
    pass2_user = f"""Generate three plain-language outputs. Input: {json.dumps(p1, indent=2)}

{{"summary_legal": "...", "summary_plain": "WHAT HAPPENED: ... THE RULE: ... WHAT THE COURT DECIDED: ... WHY THIS MAY MATTER TO YOU: ...", "attorney_prompt": "..."}}"""

    raw2 = call_deepseek(pass2_sys, pass2_user)
    p2 = extract_json(raw2)
    if not p2:
        print(f"  Pass 2 FAILED again")
        recovery_results["still_failed"].append({"cluster_id": cid, "reason": "pass2"})
        continue

    # Save
    output = {
        "cluster_id": cid,
        "case_name": meta.get('case_name', ''),
        "court": "Supreme Court of Florida" if meta.get('court_id') == 'fla' else "District Court of Appeal of Florida",
        "date_filed": meta.get('date_filed', ''),
        "cite_count": meta.get('citation_count', 0),
        "pass1": p1,
        "pass2": p2,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    with open(f"{PROCESSED}/{cid}.json", "w") as f:
        json.dump(output, f, indent=2)

    recovery_results["recovered"].append({"cluster_id": cid, "case_name": meta.get('case_name','')[:40]})
    print(f"  RECOVERED ✓")
    time.sleep(0.5)

with open(RECOVERY_LOG, "w") as f:
    json.dump(recovery_results, f, indent=2)

print(f"\n=== RECOVERY COMPLETE ===")
print(f"Recovered: {len(recovery_results['recovered'])}")
print(f"Still failed: {len(recovery_results['still_failed'])}")
for f in recovery_results["still_failed"]:
    print(f"  {f['cluster_id']}: {f['reason']}")
print(f"\nLogs: {EMPTY_TAGS_LOG}, {RECOVERY_LOG}")
