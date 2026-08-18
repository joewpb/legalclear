// frontend mirror of the backend canonical disclaimer (src/core/upl.py,
// DISCLAIMER_VERSION 2). If the backend text changes, update this mirror —
// the checker verifies the two stay in sync.

export const DISCLAIMER_TEXT =
  "This is legal information from an automated tool, not a substitute " +
  "for a licensed attorney. Before filing anything or acting on a " +
  "deadline, confirm with a Florida attorney. Free help: LegalClear " +
  "/find-legal-help.";

export default function DisclaimerNote({ className }: { className?: string }) {
  return <p className={className}>{DISCLAIMER_TEXT}</p>;
}
