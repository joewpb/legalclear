#!/usr/bin/env python3
"""Recover 20 failed clusters with larger max_tokens."""
import json, os, re, requests, time, sys
from datetime import datetime, timezone

def load_key():
    for line in open(os.path.expanduser("~/.hermes/.env"), "rb").read().split(b"\n"):
        l = line.decode().strip()
        if "DEEP" in l and "API_KEY" in l and l.startswith("DEEP"):
            return l.split("=", 1)[1]
    return ""

KEY = load_key()
URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"
PROC = "/home/hermes/legal_data/processed"

def call(system, user, retries=3, maxtok=4096):
    for a in range(retries):
        try:
            r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ], "temperature": 0.1, "max_tokens": maxtok}, timeout=120)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
            elif r.status_code == 429: time.sleep(min(2**a*5, 30))
            else: return None
        except:
            if a < retries-1: time.sleep(2**a*3)
            else: return None
    return None

from json_repair import repair_json

def parse(text):
    if not text: return None
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        t = t.rsplit("```", 1)[0] if "```" in t else t
    repaired = repair_json(t)
    try: return json.loads(repaired)
    except: return None

meta = json.load(open("/home/hermes/legal_data/filtered_phase1a_clusters.json"))
clusters = {c["cluster_id"]: c for c in meta["clusters"]}

fails = [1553635, 2487703, 2532607, 2723282, 2734179, 3006439, 3193686,
         4344101, 4994330, 4997890, 5052958, 5053012, 5053256, 5053257,
         5053258, 5053314, 5053450, 5053458, 5053459, 5055336]

print(f"Retrying {len(fails)} clusters with max_tokens=4096\n")

P1_SYS = "You are a legal data extraction AI. Return ONLY valid JSON."
P2_SYS = "You are a legal plain-language AI. Return ONLY valid JSON."

recovered = []
still_failed = []

for idx, cid in enumerate(fails):
    print(f"[{idx+1}/{len(fails)}] Cluster {cid}...", end=" ")
    sys.stdout.flush()

    d = json.load(open(f"/home/hermes/legal_data/staging/{cid}.json"))
    m = clusters.get(cid, {})
    text = d.get("opinion_text", "")
    text = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', text).strip()[:50000]

    court_name = "Supreme Court of Florida" if m.get("court_id") == "fla" else "District Court of Appeal of Florida"

    # Pass 1
    u1 = f"""Extract structured data from this Florida court opinion.

Cluster ID: {cid}
Case: {m.get('case_name','')}
Court: {court_name}
Date: {m.get('date_filed','')}
Cite Count: {m.get('citation_count',0)}

TEXT:
{clean}

Return JSON with: cluster_id, case_name, court, date_filed, citation, cite_count, parties, core_facts, legal_issue, holding_raw, outcome, key_statutes, situation_tags"""

    r1 = call(P1_SYS, u1, maxtok=4096)
    p1 = parse(r1)
    if not p1:
        print("P1 FAIL")
        still_failed.append({"cluster_id": cid, "reason": "pass1"})
        continue

    # Pass 2
    u2 = f"""Generate plain-language outputs from this case data.

{p1}

Return JSON with: summary_legal, summary_plain (with WHAT HAPPENED, THE RULE, WHAT THE COURT DECIDED, WHY THIS MAY MATTER TO YOU sections), attorney_prompt"""

    r2 = call(P2_SYS, u2, maxtok=4096)
    p2 = parse(r2)
    if not p2:
        print("P2 FAIL")
        still_failed.append({"cluster_id": cid, "reason": "pass2"})
        continue

    # Save
    out = {"cluster_id": cid, "case_name": m.get('case_name',''), "court": court_name,
           "date_filed": m.get('date_filed',''), "cite_count": m.get('citation_count',0),
           "pass1": p1, "pass2": p2, "processed_at": datetime.now(timezone.utc).isoformat()}
    json.dump(out, open(f"{PROC}/{cid}.json", "w"), indent=2)
    print("RECOVERED ✓")
    recovered.append(cid)
    time.sleep(0.5)

print(f"\n=== RESULTS ===")
print(f"Recovered: {len(recovered)}")
for cid in recovered: print(f"  {cid} ✓")
print(f"Still failed: {len(still_failed)}")
for f in still_failed: print(f"  {f['cluster_id']}: {f['reason']}")
