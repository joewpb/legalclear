---
name: playwright-landmine
description: playwright is in backend/requirements.txt but unused in backend/src/; not a Mode B violation today but a future-trap
metadata:
  type: project
---

`playwright` is listed in `backend/requirements.txt` (line ~17 in the
oneshot's prescribed list) but it is **not imported anywhere in
`backend/src/`** as of 2026-05-14.

**Why this exists:** the oneshot included `playwright` so the optional
Mode B Florida portal automation could be enabled later. That option has
since been closed by policy (see [[mode-b-hardened]]), but no one
removed the dependency.

**Why it's a landmine:**
- The Phase 11 verify command greps `backend/src/` for `playwright|selenium|puppeteer`.
  If a future change ever `import`s playwright in backend code, that grep fires
  and the build dies — by design.
- A casual reader scanning `requirements.txt` might think Mode B is alive.
  It isn't.

**How to apply:**
- Do NOT add playwright imports to `backend/src/`. Ever.
- During Part B Phase 22 (Integration wire-up + polish), recommend removing
  the unused dep from `requirements.txt` to eliminate the trap.
- If Joe ever asks "why is playwright in our requirements?", the answer is
  "vestigial from the oneshot — Mode B got cut".
