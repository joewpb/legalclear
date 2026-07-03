#!/usr/bin/env python3
"""Quick test: DeepSeek API with a single opinion."""
import json, os, requests, re

def load_api_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1]
    return ""

key = load_api_key()
print(f"Key length: {len(key)}, starts: {key[:5]}...")

# Read one opinion
with open('/home/hermes/legal_data/staging/2545886.json') as f:
    opinion = json.load(f)

text = opinion['opinion_text']
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()[:3000]

resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "Extract: case_name, court, date_filed, outcome, situation_tags. Return ONLY valid JSON."},
            {"role": "user", "content": f"CLUSTER ID: 2545886\nCASE NAME: State v. Montgomery\nCOURT: Supreme Court of Florida\nDATE: 2010-04-08\nTEXT: {text}"}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    },
    timeout=60
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    raw = resp.json()['choices'][0]['message']['content']
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0] if "```" in raw else raw
    try:
        data = json.loads(raw)
        print(f"JSON parsed OK. Keys: {list(data.keys())}")
        print(f"Tags: {data.get('situation_tags', 'N/A')}")
    except json.JSONDecodeError as e:
        print(f"Parse error: {e}")
        print(f"Raw: {raw[:500]}")
else:
    print(f"Error: {resp.text[:300]}")
