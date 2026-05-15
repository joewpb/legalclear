---
name: hub-8-tiles
description: Phase 15 HomeHub has exactly 8 tiles in a fixed order — resolves the prior 6-vs-8 question
metadata:
  type: reference
---

`phases/source/PHASE_15_hub_restructure.md` specifies **exactly 8 tiles**
in fixed order:

| # | Title (uppercase, mono)        | Route             | Phase that fills it |
|---|--------------------------------|-------------------|---------------------|
| 1 | I HAVE A DOCUMENT              | `/upload`         | existing Phase 12 uploader |
| 2 | SMALL CLAIMS (FL)              | `/small-claims`   | Phase 16 |
| 3 | EXPUNGEMENT (FL)               | `/expungement`    | Phase 17 |
| 4 | LANDLORD / TENANT (FL)         | `/landlord`       | Phase 18 |
| 5 | COURT FORMS FINDER (FL)        | `/forms`          | Phase 19 |
| 6 | TRAFFIC / TICKETS (FL)         | `/traffic`        | Phase 20 |
| 7 | POLICE REPORT ANALYZER         | `/police-report`  | Phase 21 |
| 8 | FL CASE LAW LOOKUP             | `/case-law`       | Phase 22 |

Layout per source: 1 col mobile (<640px) / 2 col tablet / 4 col desktop.
Grid gap 1px (tile borders form a single lattice). Tile padding 32px.

In Phase 15, all 8 tiles route to live routes (stubs OK for #2-#8;
tile #1 reaches the existing uploader). Phases 16-22 each replace their
stub with the real tile content. Phase 23 adds `/filing-packet/:id`
(reached AFTER tile-wizard Generate, not a hub tile).

The hub introduces Brutalist design tokens
(`frontend/src/styles/brutalist.css`) that are mandatory on every
Part B component from Phase 15 onward.
