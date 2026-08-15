# Remediation Plan

> NOTE: this file did not exist when Phase A closed (2026-08-14); it was created
> then with the Phase A record. Later phases append their own sections.

## Phase A — COMPLETE (2026-08-14)

- Final code SHA: `6178604` (+ docs `d2344c8`)
- Test suite: **237 passed / 1 skipped** from a 200/1 baseline (+37, none dropped)
- Parity: clean to expectation — remaining drift is only attorney_inquiries /
  user_profiles (frozen on the RLS decision) and known column drift on
  legal_opinions, court_forms, usage_stats, users. app_config codified in
  migrations (20260814000000).
- ENVIRONMENT flipped to `production` on Railway; S3-3 startup validator active
  and passing.
- Merged (squash, each separately committed): s1-1 `30f60e2`, s3-3 `d301995`,
  s1-4 `ee90981`, s1-3 `d8c343d`, paywall-off `6a98510`, s3-4 `af61bc9`,
  s3-5a `b01e7a5`, s3-5b `63dba41`, s3-5c `fdadc69`, s3-1 `daa8e7b`,
  s2-2 `6178604`.
- Deferrals:
  - `fix/pc-upl-stale-tests` → Phase B4 (canonical-disclaimer decision; see
    FOLLOW_UPS.md DEFERRED entry).
  - Branch deletions for the three content-merged case-law branches skipped —
    harmless, Joe's own cleanup.
- Rollback point: `b82e68b`.
