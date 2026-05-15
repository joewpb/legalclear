// Shared types for the Phase 20 traffic wizard.

export type Violation = {
  type: string;
  is_civil_infraction: boolean;
  is_criminal: boolean;
  points: number;
  traffic_school_eligible: boolean;
};

export type County = {
  name: string;
  clerk_url: string;
};

export type ChosenPath = "pay" | "school" | "contest" | "";

export type TrafficForm = {
  citation_type: string;
  citation_number: string;
  issue_date: string;
  county: string;
  first_offense_12mo: boolean;
  chosen_path: ChosenPath;
};

export type ContestResult = {
  document_name: string;
  document_url: string | null;
  filing_deadline_days: number;
  filing_location: string;
  hearing_preparation_tips: string[];
};
