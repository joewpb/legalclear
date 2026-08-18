.PHONY: verify-docs verify-educational

# Mechanically prove SPEC_LEDGER.md's code/test paths and absence claims
# against the working tree. File-existence + grep assertions only.
verify-docs:
	python3 scripts/verify_docs.py

# Educational-framing standard (Decision 11 / AGENTS.md principle 2b).
# BASELINE MODE: reports violations, exits 1 while any exist. NOT a required
# CI check yet — it will be red until the G1 presentation slice lands.
verify-educational:
	python3 scripts/verify_educational.py
