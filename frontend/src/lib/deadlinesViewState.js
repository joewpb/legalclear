// Deadlines-tab view-state decision (B5 UI — three states, locked by
// deadlinesViewState.test.js).
//
// Pure function — no React, no IO — so the state boundary is unit-lockable.
//
//   (a) 'no-deadlines' : genuinely nothing. Reachable ONLY when
//       escalation_reasons is empty — showing this copy to a user who has a
//       live answer deadline running on a service date we never asked for is
//       the wrong-date failure wearing friendlier clothes.
//   (b) 'escalation'   : reasons exist and no rows — render the reasons and
//       point at the capture form; the deadline depends on user input.
//   (c) 'error'        : the request itself failed — never fabricate or
//       estimate a date.
//
// 'mixed' (reasons + rows) and 'rows' (normal case) round out the matrix;
// the component renders rows whenever they exist, escalation box on top.
export function deadlinesViewState({ state, escalation, deadlines }) {
  if (state === 'error') return { kind: 'error' };

  const hasEscalation = Boolean(
    escalation &&
      Array.isArray(escalation.escalation_reasons) &&
      escalation.escalation_reasons.length > 0
  );
  const rows = Array.isArray(deadlines) ? deadlines : [];

  if (hasEscalation) {
    return rows.length === 0
      ? { kind: 'escalation' }
      : { kind: 'mixed', rows };
  }
  if (rows.length === 0) return { kind: 'no-deadlines' };
  return { kind: 'rows', rows };
}
