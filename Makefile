.PHONY: verify-docs

# Mechanically prove SPEC_LEDGER.md's code/test paths and absence claims
# against the working tree. File-existence + grep assertions only.
verify-docs:
	python3 scripts/verify_docs.py
