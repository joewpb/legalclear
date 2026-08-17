# TASK: B4 Dispatch 1 — CONTINUATION (25 turns). Finish the SSE tolerance conversion.

This is a continuation of run 22_b4a (sonnet, exhausted its 40-turn cap at $1.29).
Branch: fix/b4a-sse-tolerance (already checked out). Do NOT redo what is done.

## Already done (VERIFIED — do not redo, do not refactor, keep it)
- frontend/src/lib/sse.ts created: shared readSSE yielding {event, data} (parses
  "event:" lines; "data:" lines; backward-compatible).
- Converted + typed-disclaimer handling added to:
  CriminalProcedureExplainer.tsx, SmallClaimsExplainer.tsx, PoliceReportAnalyzer.tsx,
  FormsFinderFL.tsx, PropertyCasualtyExplainer.tsx (the last may be PARTIAL — check it).
- Pattern used: `for await (const { event, data: chunk } of readSSE(reader))`; when
  event === "disclaimer", parse and set the disclaimer directly (never accumulate into
  the explanation JSON); unknown event types ignored gracefully.

## Remaining job (this is the ONLY job — finish and prove, 25 turns)
1. Convert the remaining inline readSSE definitions to the shared lib/sse:
   - frontend/src/components/ChatDrawer.tsx (attorney-referral chat surface)
   - frontend/src/pages/DiscoveryMotionAnalyzer.tsx
   - frontend/src/pages/WillsTrustsExplainer.tsx
   - PropertyCasualtyExplainer.tsx if its inline copy still exists (it appears in both
     lists — remove the inline one, keep the import).
   Apply the SAME pattern as the converted pages (typed disclaimer event, graceful
   ignore of unknown types, no behavior change for existing data events).
2. Verify the whole frontend compiles:
   cd frontend && npm run build 2>&1   (must exit 0)
   Run any lint script present in package.json if there is one.
3. Fix only build/lint breakage caused by the conversion. Do not touch backend.

## Rules
- No backend changes. No migrations. No secrets.
- Report: every file changed (file:line), build evidence verbatim (tail of npm build),
  and the backward-compatibility statement for existing events.
