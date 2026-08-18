#!/usr/bin/env python3
"""10% sample ratio check: owned statutes text length vs official per-section
page body length. Sample: 9 sections across ch. 34 + ch. 83."""
import os
import re
import sys
import time
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_statutes import range_dir_for, validate_record  # noqa: E402

# load env
env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
HDR = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

SAMPLE = ["83.60", "34.01", "83.232", "83.43", "34.041", "83.45", "83.57", "34.13", "83.803"]


def supabase_q(path: str):
    r = urllib.request.Request(URL + path, headers=HDR)
    return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())


def official_body_len(section: str) -> int:
    ch = section.split(".")[0]
    rng = range_dir_for(ch)
    sec = section.replace(".", ".")
    ch4 = ch.zfill(4)
    url = (f"https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute"
           f"&URL={rng}/{ch4}/Sections/{ch4}.{section.split('.')[1]}.html")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LegalClear corpus validation)"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    # body = SectionBody span content up to the HistoryTitle span
    m = re.search(r'class="SectionBody">(.*?)class="HistoryTitle">', html, re.DOTALL)
    if not m:
        return -1
    body = re.sub(r"<[^>]+>", " ", m.group(1))
    body = re.sub(r"\s+", " ", body).strip()
    return len(body)


owned = {r["section"]: (r["text"] or "") for r in supabase_q(
    f"/rest/v1/statutes?select=section,text&section=in.({','.join(SAMPLE)})")}

print(f"{'section':>9} {'owned':>7} {'official':>9} {'ratio':>6}  verdict")
for sec in SAMPLE:
    o_len = len(owned.get(sec, ""))
    off_len = official_body_len(sec)
    time.sleep(1.2)
    ratio = (o_len / off_len) if off_len > 0 else 0.0
    verdict = "OK" if 0.85 <= ratio <= 1.20 else ("TRUNCATED" if ratio < 0.85 else "EXTRA?")
    print(f"{sec:>9} {o_len:>7} {off_len:>9} {ratio:>6.2f}  {verdict}")
