// Shared types for the case-law lookup (Phase 22).

export type CourtFilterValue =
  | "all"
  | "fl_supreme"
  | "fl_appellate";

export const COURT_FILTERS: {
  value: CourtFilterValue;
  label: string;
  description: string;
}[] = [
  {
    value: "all",
    label: "All Florida courts",
    description: "Search every court level at once — best for most searches.",
  },
  {
    value: "fl_supreme",
    label: "Florida Supreme Court",
    description:
      "Florida's highest court. Its decisions are binding on all lower Florida courts.",
  },
  {
    value: "fl_appellate",
    label: "Florida District Courts of Appeal",
    description:
      "The five intermediate appeals courts. Most cases never reach the Supreme Court, so appellate decisions are often the final word.",
  },

];

export type CaseResult = {
  case_name: string;
  citation: string;
  court: string;
  date_filed: string;
  cite_count: number;
  plain_english_summary: string | null;
  courtlistener_url: string | null;
  citation_treatment: CitationTreatment[] | null;
};

export type CitationTreatment = {
  type: "overruled" | "reversed" | "superseded" | "abrogated" | "criticized" | "questioned" | "other";
  text: string;
};

export type CaseSearchResponse = {
  results: CaseResult[];
  total_results: number;
  query: string;
};

// Example searches shown in the empty state.
export const EXAMPLE_SEARCHES = [
  {
    label: "Stand your ground / self-defense",
    query: "stand your ground self defense",
  },
  {
    label: "Landlord wrongfully withholds security deposit",
    query: "landlord security deposit wrongfully withheld",
  },
  {
    label: "Car accident — determining fault",
    query: "car accident fault negligence",
  },
  {
    label: "Child custody modification",
    query: "child custody modification change circumstances",
  },
  {
    label: "Boundary dispute with neighbor",
    query: "boundary dispute adverse possession",
  },
  {
    label: "Slip and fall at a business",
    query: "slip and fall premises liability",
  },
];

// Legal aid links shown in the disclaimer.
export const LEGAL_AID_LINKS = [
  {
    label: "Florida Law Help (free legal aid finder)",
    url: "https://floridalawhelp.org",
  },
  {
    label: "LegalClear Attorney Referral — connect with a Florida lawyer",
    url: "/attorney-referral",
  },
];
