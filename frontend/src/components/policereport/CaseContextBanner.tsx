import type { CaseContext, UserRole, ReportType } from "./types";

const ROLE_LABELS: Record<UserRole, string> = {
  suspect: "Suspect / Defendant",
  personOfInterest: "Person of Interest",
  victim: "Victim",
  complainant: "Complainant",
  witness: "Witness",
  involvedDriver: "Involved Driver",
  citationHolder: "Citation Holder",
  juvenile: "Juvenile",
  other: "Other Party",
  unclear: "Unclear",
};

const REPORT_LABELS: Record<ReportType, string> = {
  arrestReport: "Arrest Report",
  incidentReport: "Incident Report",
  crashReport: "Crash / Accident Report",
  citation: "Traffic Citation",
  juvenileReport: "Juvenile Report",
  unknown: "Unknown",
};

const CONFIDENCE_THRESHOLD = 0.5;

export default function CaseContextBanner({
  caseContext,
}: {
  caseContext: CaseContext;
}) {
  const { userRole, reportType, routingConfidence } = caseContext.routing;
  const isUncertain =
    routingConfidence < CONFIDENCE_THRESHOLD ||
    userRole === "unclear" ||
    userRole === "other";

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        padding: 16,
        margin: "0 0 16px 0",
        display: "grid",
        gap: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          justifyContent: "space-between",
          flexWrap: "wrap",
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 11,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          DOCUMENT CONTEXT
        </span>
        <span
          className="mono"
          style={{ fontSize: 12, color: "var(--muted)" }}
        >
          {REPORT_LABELS[reportType] ?? reportType}
        </span>
      </div>

      {isUncertain ? (
        <p style={{ margin: 0, lineHeight: 1.5 }}>
          This report's role could not be determined automatically. Confirm
          with your attorney which party you are.
        </p>
      ) : (
        <p style={{ margin: 0, lineHeight: 1.5 }}>
          This report identifies you as:{" "}
          <strong>{ROLE_LABELS[userRole] ?? userRole}</strong>
        </p>
      )}

      <div
        style={{
          border: "1px solid var(--border)",
          padding: 12,
          background: "var(--bg-elevated, transparent)",
        }}
      >
        <p
          className="mono"
          style={{
            margin: "0 0 4px",
            fontSize: 11,
            color: "var(--muted)",
            letterSpacing: "0.08em",
          }}
        >
          NOTE
        </p>
        <p style={{ margin: 0, lineHeight: 1.5, fontSize: 13 }}>
          Role detection is based on document text only. Always confirm with a
          licensed Florida attorney before taking any action.
        </p>
      </div>
    </div>
  );
}
