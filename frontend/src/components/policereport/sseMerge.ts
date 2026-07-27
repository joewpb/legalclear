// Pure reducer for the Police Report /analyze SSE merge.
//
// Extracted from PoliceReportAnalyzer.tsx so the merge semantics are
// independently unit-testable. The merge must be ORDER-INDEPENDENT for the
// typed-event fields: `risk_analysis`, `relevant_opinions`, and
// `situation_tags_used` must survive any later `analysis_json` merge even
// when that payload omits them. The original showstopper bug was exactly a
// final analysis-JSON parse wiping `relevant_opinions` that had been set by
// the (last) typed event.
//
// Emission contract mirrored from PoliceReportAnalyzerV2.analyze_stream
// (backend/src/agents/police_report_v2.py):
//   1. raw analysis-JSON chunks  (no `type`)
//   2. risk_analysis event       (`type: "risk_analysis"`)
//   3. relevant_opinions event   (`type: "relevant_opinions"`)  ← emitted last
//   no terminal `done` event.
//
// Generic over the concrete state shape `S` so the component can plug in its
// own AnalysisResponse without an index-signature clash; the merge only ever
// reads/writes the three typed-event fields plus a shallow spread.

import type { RelevantOpinion } from "./types";

/** State shape the reducer requires (the three carry-over fields, optional). */
export interface PoliceReportState {
  [k: string]: unknown;
  risk_analysis?: unknown;
  relevant_opinions?: RelevantOpinion[];
  situation_tags_used?: string[];
  case_context?: unknown;
}

export type PoliceReportSseEvent =
  // Typed event: risk score computed deterministically post-stream.
  | { type: "risk_analysis"; [k: string]: unknown }
  // Typed event: retrieved FL case law (emitted last on the happy path).
  | {
      type: "relevant_opinions";
      situation_tags_used: string[];
      opinions: RelevantOpinion[];
    }
  // Typed event: case context extraction (Phase 9).
  | {
      type: "case_context";
      case_context: unknown;
    }
  // The accumulated analysis JSON, parsed (partial during stream, final after).
  // `object` (not Record<string, unknown>) so callers can pass a precise
  // interface like AnalysisResponse that lacks a string index signature.
  | { type: "analysis_json"; data: object };

/**
 * Apply one SSE event to the accumulated response state. Pure: same inputs →
 * same output, no side effects. Order-independent for typed-event fields.
 */
export function applySseEvent<S>(prev: S, event: PoliceReportSseEvent): S {
  switch (event.type) {
    case "risk_analysis":
      // Store the whole event object (it carries the `type: "risk_analysis"`
      // discriminator that RiskAnalysis / RiskScoreCard expect). Matches the
      // prior inline `risk_analysis: solo as RiskAnalysis`.
      return { ...prev, risk_analysis: event } as S;

    case "relevant_opinions":
      return {
        ...(prev as Record<string, unknown>),
        situation_tags_used: event.situation_tags_used,
        relevant_opinions: event.opinions,
      } as S;

    case "case_context":
      return { ...prev, case_context: event.case_context } as S;

    case "analysis_json": {
      const p = prev as Record<string, unknown>;
      const d = event.data as Record<string, unknown>;
      return {
        ...p,
        ...d,
        // Carry-overs: a typed event that arrived earlier wins over an
        // analysis-JSON payload that does not re-include the field.
        risk_analysis: p.risk_analysis ?? d.risk_analysis,
        relevant_opinions: p.relevant_opinions ?? d.relevant_opinions,
        situation_tags_used: p.situation_tags_used ?? d.situation_tags_used,
        case_context: p.case_context ?? d.case_context,
      } as S;
    }
  }
}
