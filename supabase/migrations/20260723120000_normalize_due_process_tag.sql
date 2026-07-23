-- Normalize the `due process` (space) situation_tag to `due_process`
-- (underscore) so it matches the convention used by every other tag the
-- Police Report mapper emits (fourth_amendment, fifth_amendment,
-- language_access, ...). Without this, derive_situation_tags() emits
-- `due_process` but the corpus stores `due process`, so retrieval for a
-- due_process defect always returned zero opinions.
--
-- Scope: ONLY the `due process` -> `due_process` element. No other tag,
-- no other column, no other row. Idempotent: a second run is a no-op
-- because no row still contains `due process`.
--
-- Data-only UPDATE (no DDL) on the read-only legal_opinions reference
-- table. Verified against prod: exactly 4 rows currently carry the tag.

UPDATE public.legal_opinions
SET situation_tags = (
    SELECT array_agg(
        CASE WHEN elem = 'due process' THEN 'due_process' ELSE elem END
    )
    FROM unnest(situation_tags) AS elem
)
WHERE situation_tags @> ARRAY['due process']::text[];
