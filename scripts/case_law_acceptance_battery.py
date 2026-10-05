#!/usr/bin/env python3
"""Black-box acceptance battery for the LegalClear case-law search page.

Stdlib-only. Hits the deployed API (no repo access, no keys required).
Usage: python3 case_law_acceptance_battery.py [base_url] [--reps N]

Per query it reports: total_results vs rows actually shipped, junk rows
("Unknown case name"), corrupted dates (leading '2' dropped from year),
empty/'Not provided' citations, strict-JSON validity of the raw response,
and result-set stability across reps (sorted-courtlistener_url signature).
A clean battery = chips return results, case-name search works, zero junk,
zero bad dates, stable totals.
"""
import hashlib
import json
import re
import sys
import time
import urllib.request

DEFAULT_BASE = "https://zesty-delight-production-b533.up.railway.app"

# Query strings the shipped frontend sends from its example chips (bundle constants)
CHIPS = [
    "stand your ground self defense",
    "landlord security deposit wrongfully withheld",
    "car accident fault negligence",
    "child custody modification change circumstances",
    "boundary dispute adverse possession",
    "slip and fall premises liability",
]
TOKENS = [
    "murder", "battery", "theft", "dui", "marijuana", "foreclosure",
    "alimony", "negligence", "probable cause", "fourth amendment",
    "miranda", "contract", "terry stop", "eviction",
    "self-defense", "self defense", "stand your ground", "homestead",
]
CASE_NAMES = [
    "Bush v. Gore", "Dennis v. State", "Hurst v. Florida",
    "State v. Montgomery", "Terry v. Ohio", "Jardines v. State",
]
SENTINELS = ("Not provided", "Not provided in opinion")
DATE_RE = re.compile(r"^(19|20)\d\d-\d\d-\d\d$")


def search(base, query, timeout=90):
    body = json.dumps({"query": query, "court_filter": "all"}).encode()
    req = urllib.request.Request(
        f"{base}/api/case-law/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    strict_ok = True
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        strict_ok = False
        d = json.loads(raw.decode("utf-8", "replace"), strict=False)
    rows = d.get("results", []) or []
    junk = sum(1 for r in rows
               if not r.get("case_name") or r.get("case_name") == "Unknown case name")
    bad_dates = sum(1 for r in rows
                    if r.get("date_filed") and not DATE_RE.match(str(r["date_filed"])))
    empty_cite = sum(1 for r in rows if not r.get("citation"))
    sentinels = sum(1 for r in rows if r.get("citation") in SENTINELS)
    urls = [r.get("courtlistener_url", "") for r in rows]
    sig = hashlib.md5(",".join(sorted(urls)).encode()).hexdigest()[:8]
    return {
        "strict_ok": strict_ok,
        "total": d.get("total_results"),
        "n": len(rows),
        "junk": junk,
        "bad_dates": bad_dates,
        "empty_cite": empty_cite,
        "sentinels": sentinels,
        "sig": sig,
    }


def main():
    args = list(sys.argv[1:])
    base = args[0] if args and not args[0].startswith("--") else DEFAULT_BASE
    reps = 3
    if "--reps" in args:
        reps = int(args[args.index("--reps") + 1])

    print(f"base={base} reps={reps}\n")
    chip_ok, name_ok = 0, 0
    flaky, strict_fails, junk_total, baddate_total, sentinel_total = [], 0, 0, 0, 0

    for group, queries in (("CHIP", CHIPS), ("TOKEN", TOKENS), ("CASENAME", CASE_NAMES)):
        for q in queries:
            reps_out = [search(base, q) for _ in range(reps)]
            time.sleep(0.6)
            r = reps_out[0]
            sigs = {x["sig"] for x in reps_out}
            totals = {x["total"] for x in reps_out}
            stable = len(sigs) == 1 and len(totals) == 1
            strict_ok = all(x["strict_ok"] for x in reps_out)
            if not strict_ok:
                strict_fails += 1
            junk_total += r["junk"]
            baddate_total += r["bad_dates"]
            sentinel_total += r["sentinels"]
            if not stable:
                flaky.append(q)
            if group == "CHIP" and r["n"] > 0:
                chip_ok += 1
            if group == "CASENAME" and r["n"] > 0:
                name_ok += 1
            print(f"[{group:8}] {q[:38]:40} total={r['total']:>3} shipped={r['n']:>2} "
                  f"junk={r['junk']:>2} bad_dates={r['bad_dates']:>2} "
                  f"empty_cite={r['empty_cite']:>2} sentinels={r['sentinels']:>2} "
                  f"strict_json={'ok' if strict_ok else 'FAIL'} stable={'yes' if stable else 'NO'}")

    print(f"\nchips returning results: {chip_ok}/{len(CHIPS)}")
    print(f"case-name searches returning results: {name_ok}/{len(CASE_NAMES)}")
    print(f"queries with strict-JSON failures: {strict_fails}")
    print(f"flaky (nondeterministic) queries: {len(flaky)} {flaky}")
    print(f"junk rows (rep 1 sum): {junk_total}; bad dates: {baddate_total}; sentinels: {sentinel_total}")


if __name__ == "__main__":
    main()
