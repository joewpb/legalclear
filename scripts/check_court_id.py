import bz2, csv, sys
csv.field_size_limit(sys.maxsize)

fl_ids = {"4604548", "3402764", "2488783", "4640898"}

with bz2.open("/home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2", "rt", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cid = (row.get("id") or "").strip()
        if cid in fl_ids:
            court = row.get("court_id", "")
            name = (row.get("case_name") or "")[:60]
            with open("/home/joe/legal_data/debug_court_id.txt", "a") as out:
                out.write("cluster={} court_id={!r} name={}\n".format(cid, court, name))
