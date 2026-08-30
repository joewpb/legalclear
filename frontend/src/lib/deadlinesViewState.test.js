// B5 UI — three-state boundary locks for the Deadlines tab.
//
// The central guarantee (Joe, 2026-08-30): "No deadlines detected" is
// UNREACHABLE when escalation_reasons is non-empty. That copy shown to a user
// who actually has a live answer deadline is the wrong-date failure wearing
// friendlier clothes.
import { describe, expect, it } from 'vitest';
import { deadlinesViewState } from './deadlinesViewState';

const REASON =
  "The deadline for '83.60(2)' (Fla. Stat. § 83.60(2)) runs from a served date, but the only date extracted from this document is of type 'issued' (2026-08-14).";

const esc = (reasons) => ({ guidance: 'g', escalation_reasons: reasons });
const row = { id: 1, due_date: '2026-08-24' };

describe('deadlinesViewState — three-state boundary', () => {
  it("(a) no escalation + no rows → 'no-deadlines'", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: null, deadlines: [] });
    expect(v.kind).toBe('no-deadlines');
  });

  it("(a) escalation with EMPTY reasons + no rows → 'no-deadlines'", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: esc([]), deadlines: [] });
    expect(v.kind).toBe('no-deadlines');
  });

  it("(a) escalation object without a reasons array + no rows → 'no-deadlines'", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: { guidance: 'g' }, deadlines: [] });
    expect(v.kind).toBe('no-deadlines');
  });

  it("(b) non-empty reasons + no rows → 'escalation'", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: esc([REASON]), deadlines: [] });
    expect(v.kind).toBe('escalation');
  });

  it("(b) non-empty reasons + rows → 'mixed' (reasons AND rows both shown)", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: esc([REASON]), deadlines: [row] });
    expect(v.kind).toBe('mixed');
    expect(v.rows).toHaveLength(1);
  });

  it("(c) state 'error' → 'error', even with reasons and rows present", () => {
    const v = deadlinesViewState({ state: 'error', escalation: esc([REASON]), deadlines: [row] });
    expect(v.kind).toBe('error');
  });

  it('no escalation + rows → rows', () => {
    const v = deadlinesViewState({ state: 'ready', escalation: null, deadlines: [row] });
    expect(v.kind).toBe('rows');
    expect(v.rows).toHaveLength(1);
  });

  // The unreachability guarantee: for EVERY tab state, whenever
  // escalation_reasons is non-empty, the kind must never be 'no-deadlines'.
  const STATES = ['idle', 'loading', 'computing', 'ready'];
  for (const state of STATES) {
    it(`UNREACHABLE: 'no-deadlines' can never render while escalation_reasons is non-empty (state=${state})`, () => {
      for (const deadlines of [[], [row], undefined, null]) {
        const v = deadlinesViewState({
          state,
          escalation: esc([REASON, 'a second reason']),
          deadlines,
        });
        expect(v.kind).not.toBe('no-deadlines');
      }
    });
  }

  it("UNREACHABLE: even a SINGLE reason blocks 'no-deadlines'", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: esc([REASON]), deadlines: [] });
    expect(v.kind).not.toBe('no-deadlines');
  });

  it("UNREACHABLE: reasons survive when deadlines is not an array at all", () => {
    const v = deadlinesViewState({ state: 'ready', escalation: esc([REASON]), deadlines: null });
    expect(v.kind).toBe('escalation');
  });
});
