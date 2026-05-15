---
name: phase-23-shipped
description: Phase 23 done 2026-05-15 — PacketBuilder pipeline shipped; in-memory packet store + best-effort Supabase mirror; tile-generate response shape changed by design
metadata:
  type: project
---

Phase 23 shipped 2026-05-15. LegalClear v1 build target complete.

**Why this memory exists:** Phase 23 made two non-obvious shape changes
that future sessions will trip over if they don't know about them.

**1. Tile-generate response shape changed by design.**
Phases 16/17/18/20 originally returned scaffold JSON (`forms`,
`applicable_statute`, `filing_deadline_days`, etc.). Phase 23 replaced
all of those with the canonical `{packet_id, fee_usd, file_count,
checkout_url}` shape. The original `test_phase_{16,17,18,20}.py` files
were updated in place to assert the new contract; the statute and
deadline invariants are still proven, but now via content checks
against `backend/src/data/instructions_en.json` (where the citations
actually live, baked into the rendered PDF cover sheets).

If a future change reverts an endpoint to the old scaffold shape, the
phase 23 tests will pass but the phase 16/17/18/20 ones will fail with
"missing packet_id." That's the signal that the wiring is broken.

**2. Packet persistence is in-memory by design.**
`backend/src/services/packet_builder.py` keeps a module-level
`_PACKETS: dict[str, dict]` as the source of truth for packet metadata.
The Supabase mirror is best-effort and skipped silently if the
`packets` table is missing (so dev/test environments without the
migration don't fail builds). Migration SQL lives at
`backend/migrations/2026_05_15_packets.sql` and must be run against
production Supabase before Stripe webhook traffic starts flowing.

**How to apply:** when adding a new tile in v1.1+, follow the Phase 23
pattern — call `build_packet_with_checkout()` from
`src.api.routers.packet`, return its output verbatim. Don't reach
into `_PACKETS` directly from new code; use the `get_packet` /
`mark_packet_paid` / `track_packet_filing` helpers in
`packet_builder.py`.
