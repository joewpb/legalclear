// Shared types for the Phase 22 case-law lookup.

export type CourtFilterValue =
  | "all"
  | "fl_supreme"
  | "fl_appellate"
  | "federal_fl";

export const COURT_FILTERS: { value: CourtFilterValue; label: string }[] = [
  { value: "all", label: "All" },
  { value: "fl_supreme", label: "FL Supreme" },
  { value: "fl_appellate", label: "FL Appellate" },
  { value: "federal_fl", label: "Federal applying FL law" },
];

export type CaseResult = {
  case_name: string;
  citation: string;
  court: string;
  date_filed: string;
  plain_english_summary: string | null;
  courtlistener_url: string | null;
};

export type CaseSearchResponse = {
  results: CaseResult[];
  total_results: number;
  query: string;
};
