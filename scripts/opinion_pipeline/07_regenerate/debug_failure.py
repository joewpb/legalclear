#!/usr/bin/env python3
"""Debug one failed cluster."""
import json, os, re, requests

def load_key():
    for line in open(os.path.expanduser("~/.hermes/.env"), "rb").read().split(b"\n"):
        l = line.decode().strip()
        if "DEEP" in l and "API_KEY" in l and l.startswith("DEEP"):
            return l.split("=", 1)[1]
    return ""

KEY = load_key()
print(f"Key loaded: {len(KEY)} chars")

cid = 1553635
meta = json.load(open("/home/hermes/legal_data/filtered_phase1a_clusters.json"))
clusters = {c["cluster_id"]: c for c in meta["clusters"]}
m = clusters.get(cid, {})

staging = json.load(open(f"/home/hermes/legal_data/staging/{cid}.json"))
text = staging.get("opinion_text", "")
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()[:2000]

sys_prompt = "You are a legal data extraction AI. Return ONLY valid JSON."
user_prompt = f"""Extract: cluster_id={cid}, case_name, court, date_filed, holding, situation_tags.
Text: {text}
Return JSON only."""

resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json={"model": "deepseek-v4-flash", "messages": [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ], "temperature": 0.1, "max_tokens": 2000},
    timeout=60
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    raw = resp.json()["choices"][0]["message"]["content"]
    print(f"Raw ({len(raw)} chars):\n{raw[:500]}")
else:
    print(f"Error: {resp.text[:500]}")
