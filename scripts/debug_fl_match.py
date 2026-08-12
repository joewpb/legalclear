"""Debug: check if FL cluster IDs match rows in the clusters CSV."""
import bz2, csv, sys
csv.field_size_limit(sys.maxsize)

# Load first FL cluster IDs
fl_ids = set()
with open("/home/joe/legal_data/fl_cluster_court.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        fl_ids.add(row["cluster_id"].strip())
        if len(fl_ids) >= 100:
            break

print(f"Loaded {len(fl_ids)} FL cluster IDs for test")
print(f"Sample: {list(fl_ids)[:5]}")

# Check if they appear in CSV
with bz2.open("/home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2", "rt", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        cid_raw = row.get("id", "")
        if cid_raw is None:
            continue
        cid = cid_raw.strip()
        if cid in fl_ids:
            history = (row.get("history") or "").strip()
            cc_raw = (row.get("citation_count") or "0").strip()
            name = (row.get("case_name") or "")[:60]
            
            # Try to parse citation_count safely
            try:
                cc = int(cc_raw) if cc_raw.isdigit() else 0
            except:
                cc = 0
            
            print("FOUND cluster {}: {}".format(cid, name))
            print("  citation_count raw: {} -> {}".format(cc_raw[:100], cc))
            print("  history: {}".format(history[:200] if history else "(empty)"))
            print("  disposition: {}".format((row.get("disposition") or "(empty)")[:100]))
            break
        
        if i > 200000:
            print("Searched 200K rows, no FL cluster found")
            # Show what IDs exist in first rows
            if i < 10:
                print("  row {}: id={}".format(i, cid))
            break
