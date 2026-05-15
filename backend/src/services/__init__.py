"""Backend services — Phase 23 PacketBuilder + helpers.

This package houses the unified packet pipeline (cover sheet + walkthrough
+ form-fields summary → ZIP), the Playwright/pikepdf PDF/A renderer, the
67-county router, and the EN/ES translation layer.

Per source spec (`phases/source/PHASE_23_packet_builder.md`):
- `packet_builder.py` is called by every tile's `/generate` endpoint
- `pdfa_generator.py` runs Jinja2 → headless Chromium → pikepdf metadata
- `county_router.py` returns clerk details and fee tiers
- `translation_layer.py` looks up EN/ES templates + instructions
"""
