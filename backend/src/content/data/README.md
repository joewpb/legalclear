# Content seed data

Empty in Dispatch I-2a — this directory ships with the schema and loader
only. Dispatch I-2b fills it with the fire peril's seed rows.

## Format

One JSON object per line (`.jsonl`), one file per peril (or however the
authoring dispatch chooses to split files — the loader reads every `*.jsonl`
file in this directory regardless of name). Each line must validate against
`src.content.models.ContentRecord` — see that module for the full field
list, and `docs/pc-claim-guide-module.md` §2 for the narrative schema.

Required on every record: `phase_id`, `peril`, `jurisdiction` (`"FL"`),
`policy_inception_after` (an ISO date, or the literal string `"any"`),
`sequence`, `title`, `plain_summary`, `authority` (non-empty list of
citation strings), `effective_date`, `version`.

- Every `authority` citation must resolve against
  `src.agents.pc_citations.PC_CURATED_CITATIONS` — the loader fails the
  entire load, by name, on any citation that doesn't. Do not add a citation
  here without first adding it to the curated set.
- Every `do_now` entry requires `why`; every `never_do` entry requires
  `consequence` — these fields are the material the conditional-pair
  renderer consumes (Decision 13 voice). Content without them is invalid,
  not merely thin.
- `sequence` must be unique among all active records that share a `peril`
  value.
- Multiple versions of the same `phase_id` may coexist in the seed files;
  the loader returns only the newest version per `phase_id`. Superseded
  records should set `superseded_by` to the version that replaced them.
