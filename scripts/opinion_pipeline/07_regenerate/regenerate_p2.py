#!/usr/bin/env python3
"""Regenerate Pass 2 for 2 known-bad records."""
import json, os, re, requests, time, sys

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

P2_SYS = "You are a legal plain-language AI for LegalClear. Return ONLY valid JSON."

def call(system, user, maxtok=4096):
    for a in range(3):
        try:
            r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ], "temperature": 0.1, "max_tokens": maxtok}, timeout=120)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            elif r.status_code == 429:
                time.sleep(min(2**a*5, 30))
            else:
                return None
        except:
            if a < 2: time.sleep(2**a*3)
            else: return None
    return None

def parse(text):
    if not text: return None
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n",1)[1] if "\n" in t else t[3:]
        t = t.rsplit("```",1)[0] if "```" in t else t
    from json_repair import repair_json
    repaired = repair_json(t)
    try: return json.loads(repaired)
    except: return None

for cid in [2545071, 3218832]:
    print(f"\n=== Regenerating {cid} ===")
    d = json.load(open(f"{PROC}/{cid}.json"))
    p1 = d.get("pass1", {})

    user = f"""Generate plain-language outputs from this case data. 
summary_plain MUST contain all four labeled sections in order: WHAT HAPPENED / THE RULE / WHAT THE COURT DECIDED / WHY THIS MAY MATTER TO YOU.
Each section must be substantial (not truncated).

{p1}

Return JSON with: summary_legal, summary_plain, attorney_prompt"""

    raw = call(P2_SYS, user)
    p2 = parse(raw)

    if p2:
        d["pass2"] = p2
        json.dump(d, open(f"{PROC}/{cid}.json","w"), indent=2)
        sp = p2.get("summary_plain", "")
        labels = all(x in sp for x in ["WHAT HAPPENED", "THE RULE", "WHAT THE COURT DECIDED", "WHY THIS MAY MATTER"])
        print(f"  summary_plain len: {len(sp)}")
        print(f"  All 4 labels: {labels}")
        print(f"\n  FULL summary_plain:\n{sp}")
    else:
        print(f"  FAILED - could not regenerate")
    time.sleep(1)
