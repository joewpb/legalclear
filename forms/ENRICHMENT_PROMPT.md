# Form enrichment task (hand to a CHEAP model — Haiku is ideal)

You are enriching a catalog of Florida court forms for LegalClear. This is the
token-heavy pass: read each form's text and produce search metadata + a plain
summary. **Pure text generation — no database access, no tools beyond reading files.**

## CRITICAL RULES
- **Legal INFORMATION, never legal advice.** Describe what a form is and who
  uses it. Never tell a user what they "should" do or predict an outcome.
- **Do not invent.** If a form's text is empty, garbled, or you can't tell what
  it is, set `plain_language_summary` to `null` and `situation_tags` to `[]`.
  Skipping is correct; guessing is not.
- Florida context. English only.

## INPUT
`forms/forms_to_enrich.json` — an array. Each entry:
```json
{
  "form_number": "12.901(b)(1)",
  "title": "PETITION FOR DISSOLUTION OF MARRIAGE WITH DEPENDENT OR",
  "needs_title": true,              // if true, the scraped title is bad — propose a clean one
  "category": "family_law_dissolution",
  "status": "published",            // or "review"
  "char_count": 18234,
  "text_file": "text/12.901_b__1_.txt",   // path RELATIVE to the forms/ dir; read it for full text
  "text_excerpt": "first 4000 chars ..."  // fallback if you can't read the file
}
```
Read the full text from `forms/<text_file>` when you can; otherwise use `text_excerpt`.

## FOR EACH FORM, PRODUCE
- `plain_language_summary` — 2–4 sentences, plain English: what the form is,
  who files it, and when it's used. No advice, no outcomes.
- `situation_tags` — 3–8 lowercase snake_case keywords describing the user
  situations this form fits (e.g. `["divorce","minor_children","petitioner","child_support"]`).
  These power "type your situation → find the form" search, so think about the
  words a self-represented person would use.
- `title` — **only when `needs_title` is true**: the clean official form title,
  taken from the form's own heading text (e.g. `"Petition for Dissolution of
  Marriage with Dependent or Minor Child(ren)"`). Omit the field otherwise.

## OUTPUT
Write `forms/enrichment_output.json` — an array of objects:
```json
[
  {
    "form_number": "12.901(b)(1)",
    "plain_language_summary": "This form starts a divorce when the couple has minor or dependent children. The spouse who files (the petitioner) uses it to ask the court to end the marriage and to address parenting, time-sharing, and child support.",
    "situation_tags": ["divorce","minor_children","petitioner","child_support","time_sharing"],
    "title": "Petition for Dissolution of Marriage with Dependent or Minor Child(ren)"
  }
]
```
- `form_number` MUST match the input exactly (it's the join key).
- Process all entries (both `published` and `review`). Work in batches; keep
  summary style consistent across forms.

## WHEN DONE
Hand `forms/enrichment_output.json` back. The LegalClear side validates and
writes it to the database with:
```
cd backend
uv run python ../scripts/writeback_form_enrichment.py ../forms/enrichment_output.json            # validate
uv run python ../scripts/writeback_form_enrichment.py ../forms/enrichment_output.json --execute   # write
```
