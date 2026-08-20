#!/usr/bin/env python3
"""Post-load ratio sampling, v2: fetch each row's OWN source_url (no URL
reconstruction), look up by citation suffix."""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SAMPLE = [
    ("0001", "1.01"), ("0027", "27.52"), ("0034", "34.01"), ("0083", "83.60"),
    ("0316", "316.193"), ("0400", "400.01"), ("0509", "509.241"), ("0627", "627.70132"),
    ("0775", "775.082"), ("0894", "894.001"), ("0948", "948.06"), ("1003", "1003.01"),
]

STAGE = Path("/tmp/orin_statutes")


def find_row(ch: str, sec: str):
    f = STAGE / f"statutes_ch_{ch}.jsonl"
    if not f.exists():
        return None, f"stage file missing: {f.name}"
    for line in f.read_text().splitlines():
        r = json.loads(line)
        if r.get("section") == sec or (r.get("citation") or "").replace("\u00a7", "").endswith(sec):
            return r, None
    # fall back: list what sections exist (first 5)
    import itertools
    with open(f) as fh:
        heads = [json.loads(x).get("section") for x in itertools.islice(fh, 5)]
    return None, f"section {sec} not in file (first sections: {heads})"


def official_body_len(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    m = re.search(r'class="SectionBody">(.*?)class="HistoryTitle">', html, re.DOTALL)
    if not m:
        return -1
    body = re.sub(r"<[^>]+>", " ", m.group(1))
    return len(re.sub(r"\s+", " ", body).strip())


for ch, sec in SAMPLE:
    row, err = find_row(ch, sec)
    if row is None:
        print(f"  ch {ch} {sec}: {err}")
        continue
    own = len(row.get("text") or "")
    src = row.get("source_url") or ""
    try:
        off = official_body_len(src)
        if off <= 0:
            print(f"  ch {ch} {sec}: owned={own} official=EXTRACT-FAIL {src}")
            continue
        ratio = own / off
        flag = "OK" if 0.5 <= ratio <= 2.0 else "FLAG"
        print(f"  ch {ch} {sec}: owned={own} official={off} ratio={ratio:.2f} {flag}")
    except Exception as e:  # noqa: BLE001
        print(f"  ch {ch} {sec}: FETCH ERROR {type(e).__name__}: {e}")
    time.sleep(1.0)
