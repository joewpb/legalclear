---
name: mode-b-hardened
description: No automation against myflcourtaccess.com from backend/src/ — Phase 23 test_no_mode_b enforces this with a hard string scan
metadata:
  type: project
---

The hard rule, taken straight from `phases/source/PHASE_23_packet_builder.md`:

> **No automation against `myflcourtaccess.com`.** Phase 23 has a hard test
> (`test_no_mode_b`) that scans every Python file in `backend/src/` for the
> literal string `myflcourtaccess`. Any non-commented match fails the build.
> The walkthrough TEXT may reference the URL — but no Python code may
> navigate to it via Playwright or any HTTP client.

**Why:** LegalClear *guides* a filing; it does not *perform* a filing on
the user's behalf. Crossing this boundary changes the product's legal
posture entirely.

**The Phase 23 `test_no_mode_b` allow-list rule:**
- A file in `backend/src/` may contain the string `myflcourtaccess` ONLY if
  the same file also contains a `# walkthrough text only` comment.
- Walkthrough strings (e.g., "Go to myflcourtaccess.com and log in") are
  acceptable as data/text. HTTP clients hitting that domain are not.

**Playwright is permitted** — and Phase 23 actively uses it for headless
Chromium → PDF conversion in `pdfa_generator.py`. The previous
"playwright-landmine" memory was wrong; deleted.

**Known latent failure of `test_no_mode_b`:**
- `backend/src/platforms/florida_courts.py` (Phase 11) contains 5
  unmarked `myflcourtaccess` references. Phase 23 source explicitly
  anticipates this — "Phase 23 replaces this module's PDF generation
  with the unified packet_builder.py + pdfa_generator.py ... After
  Phase 23, `florida_courts.py` may be deprecated to a thin wrapper or
  removed." Resolution path: Phase 23 either deprecates the file or adds
  the marker comment.

**How to apply:**
- Any NEW file under `backend/src/` that imports `playwright` for
  browser navigation (`page.goto`, `browser.new_page` against a URL),
  rather than for headless PDF rendering of local HTML, is a violation.
- The Phase 11 walkthrough/instruction strings are tolerated *until*
  Phase 23 — at Phase 23 time, resolve via the source's plan (deprecate
  the file or annotate it).
- Phase 20 (Traffic) and any other Part B phase that needs to "send the
  user to" myflcourtaccess.com does so in static walkthrough text only.
- `selenium`, `puppeteer`, `requests.get` / `httpx.get` against the
  domain are all violations.
