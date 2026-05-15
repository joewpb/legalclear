---
name: mode-b-hardened
description: Mode B automation is banned in backend/src/ per AGENTS.md §7; oneshot's optional Florida portal automation is superseded
metadata:
  type: project
---

Mode B (browser-automation filing of Florida court forms via the user's
own portal credentials) is **forbidden anywhere in `backend/src/`**.

**Why:** AGENTS.md §7 lists Mode B in `backend/src/` as a hard fail. The
oneshot originally left the door open — Phase 14's final banner
referenced `FLORIDA_PORTAL_EMAIL` and `FLORIDA_PORTAL_PASSWORD` env
vars as an opt-in "Mode B" path. That door is now closed by policy.

**How to apply:**
- `florida_courts.py` is the Mode A walkthrough/PDF generator only.
  PDFAGenerator + CountyRouter + ManualFilingHelper. No browser drivers.
- Any new code in `backend/src/` that imports `playwright`, `selenium`,
  or `puppeteer`, or that calls `browser.new()` / `page.goto()`, fails
  the build immediately. Phase 11 verify explicitly greps for these.
- `playwright` IS currently listed in `backend/requirements.txt` but
  not imported anywhere in `backend/src/`. That is a landmine, not a
  violation today (see [[playwright-landmine]]).
- Phase 20 (Part B walkthrough) explicitly states "no Mode B" — it
  extends Mode A with a step-by-step manual filing UI for
  myflcourtaccess.com.

The user-facing message stays: LegalClear *guides* a filing, it does not
*perform* a filing on the user's behalf.
