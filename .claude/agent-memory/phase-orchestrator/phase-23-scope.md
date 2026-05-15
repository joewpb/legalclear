---
name: phase-23-scope
description: Phase 23 is one phase but the heaviest — PacketBuilder + PDF/A + EN/ES templates + $35 Stripe + tracker + test_full_v1; resolves the prior "one phase or 9-way split" question
metadata:
  type: reference
---

**Phase 23 is a single phase**, not a 9-way verification split.

It is the heaviest phase in the build: full file inventory from
`phases/source/PHASE_23_packet_builder.md`:

**New services** (`backend/src/services/`):
- `packet_builder.py` — unified PacketBuilder; called by every tile's
  /generate endpoint
- `pdfa_generator.py` — Jinja2 → Playwright headless Chromium PDF →
  pikepdf PDF/A-1b metadata
- `county_router.py` — county-specific clerk info + fees
- `translation_layer.py` — EN/ES template lookup, pre-translated (no
  live LLM translation)

**New route** (`backend/src/api/routes/packet.py`):
- `POST /api/packet/build` — generates packet + Stripe checkout
- `GET /api/packet/{id}` — packet metadata
- `GET /api/packet/{id}/download` — gated; 402 until paid
- `POST /api/packet/{id}/track` — confirmation-number tracker

**Templates** (`backend/src/templates/`):
- `cover_sheets/{packet_type}_{en,es}.html` for 6 packet types
  (small_claims, expungement, landlord_deposit, landlord_repairs,
  landlord_eviction, traffic) × 2 langs = 12 cover sheet templates
- `cover_sheets/_form_fields_summary.html`
- `walkthroughs/manual_upload_{en,es}.html`

**Data files** (`backend/src/data/`):
- `fl_county_clerk_details.json` — all 67 counties with clerk URL,
  address, phone, fee tiers
- `instructions_{en,es}.json` — all 6 packet types in both langs;
  Spanish must use U.S. court interpreter register
- `walkthrough_steps_{en,es}.json` — ≥8 steps each, manual upload
  guide for myflcourtaccess.com

**DB schema addition:**
- New `packets` table (Phase 08 Supabase migration adds it)
- Webhook extended (Phase 09 internals untouched — adds a new branch
  for `checkout.session.completed` events with `packet_id` metadata)

**New frontend page** (`frontend/src/pages/FilingPacket.tsx`) + 5
components (`PacketSummary`, `LanguageToggle`, `PaymentGate`,
`UploadWalkthrough`, `FilingTracker`).

**Wires existing tile endpoints** — Phase 16/17/18/20 `/generate`
endpoints stop returning scaffold JSON and instead call
`build_packet()`. Response shape becomes
`{packet_id, fee_usd, file_count, checkout_url}`. Tile review steps
navigate to `/filing-packet/:packetId`.

**New dependencies:** `uv add pikepdf jinja2` (Playwright already
present). Requires `backend/pyproject.toml` to exist — see
[[part-a-source-divergences]] divergence #1.

**Tests:**
- `backend/tests/test_phase_23.py` — 10 assertions
- `backend/tests/test_full_v1.py` — 4 assertions (full-system smoke)

**Hardest test:** `test_no_mode_b` — scans every `.py` under
`backend/src/` for the literal string `myflcourtaccess`. Any
non-commented match fails the build. See [[mode-b-hardened]].

**Final report:** Phase 23 emits the canonical v1 deployment report
block. If any Phase 23 assertion fails, no report.

**How to apply:** when planning Phase 23, allocate the budget as if it
were 3-4 phases stacked into one. Most of Part B's database, payment,
and PDF complexity lives here. Phases 16-20 deliberately scaffold
their /generate endpoints with stub JSON + `# TODO: replace with real
Claude-generated output` markers — Phase 23 is where those TODOs get
resolved.
