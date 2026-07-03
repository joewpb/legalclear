#!/usr/bin/env python3
"""Fix summary_plain records that were saved as dicts instead of labeled strings."""
import json, os, re

PROC = "/home/hermes/legal_data/processed"

def dict_to_string(d):
    """Convert a dict-formatted summary_plain into the labeled string format."""
    if isinstance(d, str):
        # Try to parse as JSON dict
        if d.strip().startswith("{"):
            try:
                d = json.loads(d)
            except:
                return d  # Return as-is if unparseable
        else:
            return d  # Already a string

    if not isinstance(d, dict):
        return str(d)

    sections = {
        "WHAT HAPPENED": None,
        "THE RULE": None,
        "WHAT THE COURT DECIDED": None,
        "WHY THIS MAY MATTER TO YOU": None
    }

    # Try various key formats (underscore, colon, or exact match)
    for key in d:
        key_upper = key.upper().replace("_", " ").replace(":", "").strip()
        for section_name in sections:
            if section_name in key_upper:
                sections[section_name] = d[key]
                break

    # Build the string
    parts = []
    for section_name in sections:
        content = sections[section_name]
        if content:
            parts.append(f"{section_name}: {content.strip()}")

    result = "\n\n".join(parts)
    return result if result else str(d)

# Scan and fix
files = sorted(os.listdir(PROC))
fixed = 0
already_good = 0
errors = []

for fname in files:
    if not fname.endswith('.json'): continue
    path = f"{PROC}/{fname}"
    d = json.load(open(path))
    sp = d.get('pass2', {}).get('summary_plain', '')

    if isinstance(sp, dict) or (isinstance(sp, str) and sp.strip().startswith("{")):
        # Reformat
        fixed_str = dict_to_string(sp)
        d['pass2']['summary_plain'] = fixed_str
        # Validate it has the format we want
        if "WHAT HAPPENED" in fixed_str and "THE RULE" in fixed_str:
            json.dump(d, open(path, "w"), indent=2)
            fixed += 1
        else:
            errors.append(fname.replace('.json',''))
    else:
        already_good += 1

print(f"Already correct: {already_good}")
print(f"Fixed (dict→string): {fixed}")
print(f"Errors (could not reformat): {len(errors)}")
for cid in errors[:10]:
    d = json.load(open(f"{PROC}/{cid}.json"))
    print(f"  {cid}: raw={str(d.get('pass2',{}).get('summary_plain',''))[:100]}")
