You are on branch fix/b4d-url-filter with uncommitted work from a prior run that exhausted
its turns. The filter utility is done and 8 agents are already wired. Do not redo any of it.
Do not re-explore the repo. Do not refactor the filter.

Already done — leave alone:
- url_filter.py and its 15 unit tests
- Wired: small_claims, discovery_motion, wills_trusts, explainer, chat_expert,
  police_report_v2, property_casualty, criminal_procedure

Your only job: wire form_guide.py and expungement.py to the same filter, mirroring the
pattern used by the 8 already done. Add their integration tests in the same shape as the
existing ones. Change nothing else.

Then run the full suite and report counts. Do not commit.

If the pattern does not apply cleanly to either agent, STOP and explain rather than
improvising a variant.
