#!/usr/bin/env python3
"""Post-load validation of the 636-chapter statutes corpus (Job 1 check).

1. Body detection across the full corpus: length distribution + rows under
   threshold, grouped by chapter, named individually.
2. Ratio sampling: 14 sections spanning chapters (1, 27, 34, 83, 316, 400,
   509, 627, 775, 894, 948, 1003) — owned text length vs official per-section
   page body length.
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

STAGE = Path("/tmp/orin_statutes")

# ---- 1. body detection over the staged corpus ----
lens_by_ch: dict[str, list[int]] = {}
stubs: list[str] = []
total = 0
for f in sorted(STAGE.glob("statutes_*.jsonl")):
    ch = f.name.split("_ch_")[1].split(".")[0]
    lens_by_ch[ch] = []
    for line in f.read_text().splitlines():
        r = json.loads(line)
        t = r.get("text") or ""
        lens_by_ch[ch].append(len(t))
        total += 1
        if len(t) < 120:
            stubs.append(f"{r.get('citation', ch)} ({len(t)})")

under120 = sum(1 for ls in lens_by_ch.values() for l in ls if l < 120)
under200 = sum(1 for ls in lens_by_ch.values() for l in ls if l < 200)
all_lens = sorted(l for ls in lens_by_ch.values() for l in ls)
print(f"corpus: {total} rows | min {all_lens[0]} | median {all_lens[total//2]} | max {all_lens[-1]}")
print(f"rows <120 chars: {under120} | rows <200: {under200}")
print(f"stub-suspect rows ({len(stubs)}):")
for s in stubs[:40]:
    print(f"  {s}")

# ---- 2. ratio sampling vs official per-section pages ----
SAMPLE = [
    ("0001", "1.01"), ("0027", "27.52"), ("0034", "34.01"), ("0083", "83.60"),
    ("0316", "316.193"), ("0400", "400.01"), ("0509", "509.241"), ("0627", "627.70132"),
    ("0775", "775.082"), ("0894", "894.001"), ("0948", "948.06"), ("1003", "1003.01"),
]

def owned_len(ch: str, sec: str) -> int:
    f = STAGE / f"statutes_ch_{ch}.jsonl"
    if not f.exists():
        return -1
    for line in f.read_text().splitlines():
        r = json.loads(line)
        if r.get("section") == sec or r.get("citation", "").endswith(sec):
            return len(r.get("text") or "")
    return -1

def official_body_len(ch4: str, sec: str) -> int:
    rng = f"{int(ch4[:2]):04d}-{(int(ch4[:2]) + 1) * 100 - 1:04d}"
    url = (f"https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute"
           f"&URL={rng}/{ch4}/Sections/{ch4}.{sec.split('.')[1]}.html")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    m = re.search(r'class="SectionBody">(.*?)class="HistoryTitle">', html, re.DOTALL)
    if not m:
        return -1
    body = re.sub(r"<[^>]+>", " ", m.group(1))
    return len(re.sub(r"\s+", " ", body).strip())
    time.sleep(1.0)

print("\nratio sample (owned vs official body):")
for ch, sec in SAMPLE:
    ch4 = ch.zfill(4)
    try:
        own = owned_len(ch, sec)
        off = official_body_len(ch4, sec)
        if own <= 0 or off <= 0:
            print(f"  ch {ch} {sec}: owned={own} official={off} -> CHECK FAILED")
            continue
        ratio = own / off
        flag = "OK" if 0.5 <= ratio <= 2.0 else "FLAG"
        print(f"  ch {ch} {sec}: owned={own} official={off} ratio={ratio:.2f} {flag}")
    except Exception as e:  # noqa: BLE001
        print(f"  ch {ch} {sec}: ERROR {type(e).__name__}: {e}")
    time.sleep(1.0)
