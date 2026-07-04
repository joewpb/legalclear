// Adversarial replay tests for the Police Report /analyze SSE merge reducer.
//
// The original showstopper: a final analysis-JSON parse wiped
// `relevant_opinions` (set by the last typed event) because the merge spread
// `parsed` over `prev` without carrying the typed-event keys. A test written
// from the "assumed" order (relevant_opinions last, never followed by
// anything) would NOT catch it. These tests assert ORDER-INDEPENDENCE instead:
// the typed-event fields must survive any later analysis-JSON or risk-only
// event, in any order.

import { describe, expect, it } from "vitest";
import { applySseEvent, type PoliceReportState } from "./sseMerge";
import type { RelevantOpinion } from "./types";

const ANALYSIS_JSON = {
  // A complete analysis payload — note it does NOT include risk_analysis,
  // relevant_opinions, or situation_tags_used (they arrive as separate typed
  // events). This is exactly the shape that triggered the original bug.
  incident_summary: "Officer stopped vehicle for expired tag.",
  charges_explained: [{ charge: "DUI", plain_english: "driving drunk" }],
  miranda_noted: false,
  probable_cause_present: null,
  discrepancies: [],
  missing_fields: [],
  what_happens_next: "Arraignment in 30 days.",
  disclaimer: "Legal information, not legal advice.",
};

const OPINIONS: RelevantOpinion[] = [
  {
    case_name: "State v. Doe",
    citation: "123 So. 3d 1 (Fla. 2024)",
    court: "Supreme Court of Florida",
    date_filed: "2024-01-15",
    cite_count: 12,
    outcome: "Reversed",
    summary_plain: "Miranda required once custodial.",
    summary_legal: "Fifth Amendment applies.",
    attorney_prompt: "Ask counsel about suppression.",
  },
];

const RISK_EVENT = {
  type: "risk_analysis" as const,
  score: 7,
  high_count: 2,
  medium_count: 1,
  low_count: 0,
  risk_summary: "High risk.",
  top_concerns: ["Miranda"],
};

describe("applySseEvent — real emission order (1a contract)", () => {
  it("analysis chunks → risk_analysis → relevant_opinions → final merge preserves all three", () => {
    let state: PoliceReportState = {};
    // 1. partial analysis accumulate (simulate the in-loop setResponse(parsed))
    state = { ...ANALYSIS_JSON };
    // 2. risk_analysis typed event
    state = applySseEvent(state, { ...RISK_EVENT });
    // 3. relevant_opinions typed event (emitted LAST on the happy path)
    state = applySseEvent(state, {
      type: "relevant_opinions",
      situation_tags_used: ["fifth_amendment", "dui"],
      opinions: OPINIONS,
    });
    // 4. final analysis-JSON merge after stream close
    state = applySseEvent(state, { type: "analysis_json", data: ANALYSIS_JSON });

    expect(state.relevant_opinions).toEqual(OPINIONS);
    expect(state.situation_tags_used).toEqual(["fifth_amendment", "dui"]);
    expect(state.risk_analysis).toMatchObject({ score: 7 });
    expect(state.incident_summary).toBe(ANALYSIS_JSON.incident_summary);
  });
});

describe("applySseEvent — ADVERSARIAL order-independence (the original bug)", () => {
  it("relevant_opinions survives a later analysis_json that omits it", () => {
    let state: PoliceReportState = {};
    state = applySseEvent(state, {
      type: "relevant_opinions",
      situation_tags_used: ["fourth_amendment"],
      opinions: OPINIONS,
    });
    // A later terminal event carrying only analysis fields — no opinions key.
    state = applySseEvent(state, { type: "analysis_json", data: ANALYSIS_JSON });

    expect(state.relevant_opinions).toEqual(OPINIONS);
    expect(state.situation_tags_used).toEqual(["fourth_amendment"]);
  });

  it("relevant_opinions survives a later risk_analysis-only event", () => {
    // The exact adversarial shape named in the spec: an event that sets
    // relevant_opinions, followed by a later event whose payload does NOT
    // re-include it.
    let state: PoliceReportState = {};
    state = applySseEvent(state, {
      type: "relevant_opinions",
      situation_tags_used: ["dui"],
      opinions: OPINIONS,
    });
    state = applySseEvent(state, { ...RISK_EVENT });

    expect(state.relevant_opinions).toEqual(OPINIONS);
    expect(state.situation_tags_used).toEqual(["dui"]);
    expect(state.risk_analysis).toMatchObject({ score: 7 });
  });

  it("risk_analysis survives a later analysis_json that omits it", () => {
    let state: PoliceReportState = {};
    state = applySseEvent(state, { ...RISK_EVENT });
    state = applySseEvent(state, { type: "analysis_json", data: ANALYSIS_JSON });

    expect(state.risk_analysis).toMatchObject({ score: 7 });
  });

  it("situation_tags_used survives a later analysis_json that omits it", () => {
    let state: PoliceReportState = {};
    state = applySseEvent(state, {
      type: "relevant_opinions",
      situation_tags_used: ["probable_cause"],
      opinions: [],
    });
    state = applySseEvent(state, { type: "analysis_json", data: ANALYSIS_JSON });

    expect(state.situation_tags_used).toEqual(["probable_cause"]);
  });
});
