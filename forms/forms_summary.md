# Legal Clear — Forms Manifest Summary

## Overview

| Metric | Count |
|---|---|
| Total form corpus | **167 PDFs** |
| With detectable form number | 107 (64%) |
| Without form number | 60 (36%) |
| Unique form numbers | 80 |
| Duplicate form numbers (same number, different files) | 19 |
| Scanned / failed text extraction | 14 |
| Circuits covered | 4 of 20 (5th, 10th, 11th, 19th) |

## Breakdown by Category

| Category | Count | Description |
|---|---|---|
| circuit_specific | 42 | Circuit-court local forms (motions, packets, admin orders) |
| domestic_violence | 31 | 12.980(a)–(u) — all injunction types |
| family_law_dissolution | 18 | 12.901 series + name change + miscellaneous |
| family_law_support | 16 | 12.905, 12.910–12.915 — support, relocation |
| eviction | 10 | Florida Bar tenant/landlord forms + Collier Co. packet |
| family_law_modification | 8 | 12.920–12.928 — post-judgment modification |
| family_law_procedure | 7 | 12.900 series — procedural/administrative |
| family_law_financial | 6 | 12.902 series — financial affidavits/disclosure |
| family_law_children | 6 | 12.903 series — parenting plans, timesharing |
| probate_estate | 6 | Summary/formal administration, orders |
| family_law_enforcement | 5 | 12.940, 12.941, 12.947 |
| family_law_contempt | 3 | 12.930 series — enforcement/contempt |
| family_law_misc | 3 | 12.982, 12.983, 12.995 |
| name_change | 3 | Circuit court name change packets |
| guardianship | 2 | Guardian advocacy (13th Circuit) |
| unknown | 1 | Unidentified |

## Unique Form Numbers Detected (80)

```
12.900(a), (b), (d), (e), (f), (g), (h)
12.901(a), (b)(1), (b)(2), (b)(3)
12.902(b), (c), (d), (e), (i), (j)
12.903(a), (b), (c)(1), (c)(2), (c)(3), (d)
12.904(a)(1)
12.905(a), (b), (c)
12.910(a)
12.911(a), (b), (c), (d), (e)
12.912(a), (b)
12.913(a)(1), (a)(2), (a)(3)
12.914, 12.915
12.920(a), (c)
12.921, 12.922(a), (c)
12.923, 12.927, 12.928
12.930(b), (c)
12.931(a)
12.932
12.940(e)
12.941(a), (b), (c)
12.947(a), (c)
12.980(a), (b), (c)(1), (c)(2), (d)(1), (d)(2), (e), (f), (g), (h),
          (i), (j), (k), (l), (m), (n), (o), (p), (q), (r), (t), (u)
12.982(a)
12.983(a)
12.995(a)
```

## Duplicates (Same Form Number — Multiple Files)

**Circuit duplicates** (same form, different circuit's PDF):
| Form Number | Files |
|---|---|
| 12.980(a) | Supreme Court + Circuit 19 version |
| 12.980(c)(2) | Supreme Court + Circuit 19 version |
| 12.980(g) | Supreme Court + Circuit 19 version |
| 12.980(i) | Supreme Court + Circuit 19 version |
| 12.980(j) | Supreme Court + Circuit 19 version |
| 12.980(n) | Supreme Court + Circuit 19 version |
| 12.980(o) | Supreme Court + Circuit 19 version |
| 12.980(q) | Supreme Court + Circuit 19 version |
| 12.980(r) | Supreme Court + Circuit 19 version |

**Test PDF duplicates** (test_6858xx.pdf are copies):
| Form Number | Files |
|---|---|
| 12.900(h) | `12.900_h_.pdf` + `test_685805.pdf` |
| 12.901(b)(1) | `12.901-b1.pdf` + `12.901_b__1_.pdf` (naming variant) |
| 12.901(b)(3) | `12.901_b__3_.pdf` + `test_685810.pdf` |
| 12.902(e) | `12.902_e_.pdf` + `test_685815.pdf` |
| 12.902(j) | `12.902_j_.pdf` + `test_685820.pdf` |
| 12.903(c)(2) | `12.903_c__2_.pdf` + `test_685825.pdf` |
| 12.913(a)(1) | `12.913_a__1_.pdf` + `test_685850.pdf` |

**False positives** (regex mis-match — circuit forms contain form number in filename but aren't that form):
| Form Number | Files |
|---|---|
| 12.902(d) | Supreme Court + circuit 5 parenting plan (different form) |
| 12.915 | Supreme Court + 3 circuit 5/10 forms (different forms) |
| 12.947(a) | Supreme Court + circuit 5 parenting petition (different form) |
| 12.982(a) | Supreme Court + name change packet (different form) |

## Forms with Failed Text Extraction (14)

| File | Issue |
|---|---|
| 12.980(o).pdf | Not extracted |
| 12.980_h_.pdf | Not extracted |
| 12.982_a_.pdf | Not extracted |
| 12.983_a_.pdf | Not extracted |
| circuits/circuit10/5-51.0.pdf | Not extracted (scanned image?) |
| circuits/circuit10/AO_5-20.7.pdf | Not extracted |
| circuits/circuit10/SamsHouseSupervisedVisitationAgency.pdf | Not extracted |
| circuits/circuit5/acceptance-of-service-of-supplemental-petion-and-answer.pdf | Not extracted |
| circuits/circuit5/answer-to-petition.pdf | Not extracted |
| circuits/circuit5/answer-to-supplemental-petition.pdf | Not extracted |
| circuits/circuit5/motion-to-or-for.pdf | Not extracted |
| circuits/circuit5/motion-to-suspend-terminate-child-support.pdf | Not extracted |
| circuits/circuit5/settlement-agreement-for-parties-never-married-with-children-and-instructions.pdf | Not extracted |
| circuits/circuit5/use-of-ai-in-documents.pdf | Not extracted |

## Forms Without Detectable Form Number (60)

These are circuit-local forms (motions, instructions, admin orders, self-help packets) that don't carry a Florida Supreme Court form number. They appear under:

- `circuits/circuit5/` — 22 local forms (motion templates, pretrial statements, contest packets)
- `circuits/circuit10/` — 14 local forms (IWO, self-help, admin orders)
- `circuits/circuit11/` — 2 items (OSCA plan, self-help rule)
- `circuits/circuit19/` — 1 admin order
- `eviction_*.pdf` — 10 eviction forms (Florida Bar numbered series + Collier Co. packet)
- `guardian_*.pdf` — 2 guardianship forms
- `name_change_packet_*.pdf` — 2 name change packets (8th + 13th Circuits)
- `probate_*.pdf` — 6 probate forms (formal + summary administration)
- `85054.pdf` — Department of Highway Safety document
- `test_685800.pdf`, `test_685855.pdf` — duplicate test copies

## Directory Layout

```
raw/forms/
├── forms_manifest.json          ← This inventory
├── 12.900_a_.pdf               ← 99 Supreme Court forms
├── 12.901_b__1_.pdf            ← Naming: 12.XXX(_letter)(_sub)?_.pdf
├── ...                         ← Underscores replace spaces/parens
├── eviction_*.pdf              ← 10 eviction forms
├── guardian_*.pdf              ← 2 guardianship forms
├── name_change_packet_*.pdf    ← 2 name change packets
├── probate_*.pdf               ← 6 probate forms
├── test_6858*.pdf              ← 11 test duplicate copies
├── text/                       ← Extracted plain-text (1 per PDF)
│   ├── 12.900_a_.txt
│   ├── ...
│   └── ...                     ← 167 .txt files, 3.3M chars total
└── circuits/
    ├── circuit5/               ← Fifth Judicial Circuit (22 local forms)
    ├── circuit10/              ← Tenth Judicial Circuit (14 local forms)
    ├── circuit11/              ← Eleventh Judicial Circuit (2 items)
    └── circuit19/              ← Nineteenth Judicial Circuit (11 forms)
```

## Query API

**Base URL:** `http://100.103.42.109:8088`  
**Reachability:** Accessible from any device on the same Tailscale tailnet. Not exposed to the public internet. No auth required.

### Endpoints

| Endpoint | Method | Params | Returns |
|---|---|---|---|
| `/api/forms` | GET | `?q=<keyword>` (optional) | JSON array of all 167 forms with metadata + text preview |
| `/api/forms/<id>` | GET | — | Single form JSON with full fields |
| `/api/forms/<id>/text` | GET | — | Plain text of the extracted form content |
| `/api/stats` | GET | — | Counts by category, circuit, total |
| `/forms/<path>` | GET | — | Raw PDF binary download |
| `/interview` | GET | `?case=<type>` | Guided form-selection interview |
| `/all-forms` | GET | — | Full browsable HTML index with search |

### Extracted Text Index

Flat text files also available at: `/home/hermes/wiki/raw/forms/text/<id>.txt`

Grep directly:
```bash
grep -rl "child support modification" /home/hermes/wiki/raw/forms/text/
```

### Manifest

Full structured metadata: `/home/hermes/wiki/raw/forms/forms_manifest.json`
