// Types for the Police Report Analyzer.
// Case-context facts, flagged questions, and retrieved legal reference
// material (opinions) — no original legal conclusions are generated here.

// ── Enum union types ──────────────────────────────────────────────────────────

export type UserRole =
  | "suspect"
  | "personOfInterest"
  | "victim"
  | "complainant"
  | "witness"
  | "involvedDriver"
  | "citationHolder"
  | "juvenile"
  | "other"
  | "unclear";

export type ReportType =
  | "arrestReport"
  | "incidentReport"
  | "crashReport"
  | "citation"
  | "juvenileReport"
  | "unknown";

export type DiscrepancyType =
  | "temporal"
  | "spatial"
  | "missingMiranda"
  | "probableCauseGap"
  | "inconsistentAccounts";

// ── Sub-shapes ────────────────────────────────────────────────────────────────

export type Officer = {
  name: string | null;
  badge: string | null;
  role: string | null;
};

export type Discrepancy = {
  type: DiscrepancyType;
  detail: string;
  sourceLocation: string | null;
  confidence: number;
};

// ── Top-level caseContext interface ───────────────────────────────────────────

export interface CaseContext {
  routing: {
    userRole: UserRole;
    reportType: ReportType;
    routingConfidence: number;
  };

  document: {
    agency: string | null;
    reportNumber: string | null;
    reportDate: string | null;
    extractionConfidence: number;
  };

  incident: {
    incidentDateTime: string | null;
    incidentLocation: string | null;
    incidentType: string | null;
    charges: string[];
    statuteReferences: string[];
  };

  rightsEvents: {
    arrestMade: boolean;
    searchOccurred: boolean;
    searchContext: string | null;
    mirandaMentioned: boolean;
    custodialIndicators: string[];
    statementsAttributed: boolean;
  };

  people: {
    officers: Officer[];
    otherPartiesCount: number;
  };

  discrepancies: Discrepancy[];

  sensitivity: {
    domesticViolence: boolean;
    sexualOffense: boolean;
    juvenileInvolved: boolean;
  };

  derived: {
    timelineStage: string | null;
    deadlines: any[];
    questionsForCounsel: string[];
    collateralConsequenceFlags: string[];
  };
}

// ── Factory ───────────────────────────────────────────────────────────────────

export function createEmptyCaseContext(): CaseContext {
  return {
    routing: {
      userRole: "unclear",
      reportType: "unknown",
      routingConfidence: 0,
    },
    document: {
      agency: null,
      reportNumber: null,
      reportDate: null,
      extractionConfidence: 0,
    },
    incident: {
      incidentDateTime: null,
      incidentLocation: null,
      incidentType: null,
      charges: [],
      statuteReferences: [],
    },
    rightsEvents: {
      arrestMade: false,
      searchOccurred: false,
      searchContext: null,
      mirandaMentioned: false,
      custodialIndicators: [],
      statementsAttributed: false,
    },
    people: {
      officers: [],
      otherPartiesCount: 0,
    },
    discrepancies: [],
    sensitivity: {
      domesticViolence: false,
      sexualOffense: false,
      juvenileInvolved: false,
    },
    derived: {
      timelineStage: null,
      deadlines: [],
      questionsForCounsel: [],
      collateralConsequenceFlags: [],
    },
  };
}

// ── Retrieved legal reference (opinions) ─────────────────────────────────────
// One row from the Supabase `legal_opinions` table, selected by
// situation-tag overlap. Matches the service .select() list exactly.
export interface RelevantOpinion {
  case_name: string;
  citation: string;
  court: string;
  date_filed: string | null;
  cite_count: number;
  outcome: string | null;
  summary_plain: string;
  summary_legal: string;
  attorney_prompt: string;
}
