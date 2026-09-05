/**
 * Module 3 — Police Report Analyzer page (v3).
 *
 * Mobile-first upload zone (drag-drop or tap) accepting PDF and image files.
 * Document preview alongside streaming AI analysis.
 *   - discrepancies → red alert cards
 *   - missing_fields → amber warning cards
 *   - charges_explained → expandable info cards
 */

import { useState, useRef, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";
import OpinionCard from "../components/policereport/OpinionCard";
import { applySseEvent } from "../components/policereport/sseMerge";
import type { CaseContext, RelevantOpinion } from "../components/policereport/types";
import CaseContextBanner from "../components/policereport/CaseContextBanner";
import { readSSE } from "../lib/sse";
import { DISCLAIMER_TEXT } from "../components/DisclaimerNote";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Finding {
  severity: "high" | "medium" | "low";
  description: string;
  ask_attorney: string;
  page_ref: string | null;
}

interface MissingField {
  severity: "high" | "medium" | "low";
  field_name: string;
  why_important: string;
  page_ref: string | null;
}

interface RiskAnalysis {
  type: "risk_analysis";
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  high_count: number;
  medium_count: number;
  low_count: number;
  risk_summary: string;
  top_concerns: string[];
}

interface RelevantOpinionsEvent {
  type: "relevant_opinions";
  situation_tags_used: string[];
  opinions: RelevantOpinion[];
}

interface ChargeExplained {
  charge: string;
  plain_english: string;
}

interface CitationCheckEntry {
  status: string;
  citation?: string;
  section?: string;
  chapter?: string;
  title?: string;
  adjudication?: string;
  adjudication_explanation?: string;
}

interface AnalysisResponse {
  incident_summary: string;
  parties: string[];
  charges_explained: ChargeExplained[];
  miranda_noted: boolean | null;
  probable_cause_present: boolean | null;
  probable_cause_summary: string | null;
  discrepancies: Finding[];
  missing_fields: MissingField[];
  what_happens_next: string;
  disclaimer: string;
  risk_analysis?: RiskAnalysis;
  relevant_opinions?: RelevantOpinion[];
  situation_tags_used?: string[];
  case_context?: CaseContext;
  citations_checked?: CitationCheckEntry[];
  citation_notes?: string[];
}

// ---------------------------------------------------------------------------
// SSE reader
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Severity badge (inline component)
// ---------------------------------------------------------------------------

function SeverityBadge({ severity }: { severity: string }) {
  const norm = (severity || "").toLowerCase();
  const palette =
    norm === "high"
      ? { bg: "#C62828", fg: "#fff" }
      : norm === "medium"
        ? { bg: "#F57F17", fg: "#000" }
        : { bg: "#6B6B66", fg: "#fff" };
  return (
    <span
      style={{
        background: palette.bg,
        color: palette.fg,
        padding: "2px 8px",
        borderRadius: "var(--radius, 4px)",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        display: "inline-block",
        flexShrink: 0,
      }}
    >
      {norm}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Risk score card (inline component)
// ---------------------------------------------------------------------------

function RiskScoreCard({ risk }: { risk: RiskAnalysis }) {
  const levelColor =
    risk.risk_level === "CRITICAL"
      ? "#B71C1C"
      : risk.risk_level === "HIGH"
        ? "#C62828"
        : risk.risk_level === "MEDIUM"
          ? "#F57F17"
          : "#2E7D32";

  return (
    <div
      style={{
        background: "#fff",
        border: `2px solid ${levelColor}`,
        borderRadius: "var(--radius, 4px)",
        padding: 16,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 8,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            background: levelColor,
            color: "#fff",
            padding: "4px 14px",
            borderRadius: "var(--radius, 4px)",
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: "0.05em",
          }}
        >
          {risk.risk_level} RISK
        </span>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          Score: {risk.risk_score} · {risk.high_count}H / {risk.medium_count}M /{" "}
          {risk.low_count}L
        </span>
      </div>
      <p style={{ fontSize: 14, lineHeight: 1.6, margin: "0 0 8px" }}>
        {risk.risk_summary}
      </p>
      {risk.top_concerns.length > 0 && (
        <ul
          style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.5 }}
        >
          {risk.top_concerns.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline styles
// ---------------------------------------------------------------------------

const css = {
  page: {
    maxWidth: "var(--max-page, 1140px)",
    margin: "0 auto",
    padding: "var(--space-2, 16px)",
  } as React.CSSProperties,

  header: {
    padding: "var(--space-2, 16px) 0",
  } as React.CSSProperties,

  backLink: {
    color: "var(--muted, #6B6B66)",
    fontSize: 12,
    textDecoration: "none",
  } as React.CSSProperties,

  title: {
    fontFamily: "var(--font-serif)",
    fontSize: 24,
    fontWeight: 500,
    margin: "8px 0 4px",
  } as React.CSSProperties,

  subtitle: {
    color: "var(--muted, #6B6B66)",
    fontSize: 14,
    margin: 0,
  } as React.CSSProperties,

  /* ── Upload zone ── */
  uploadZone: (dragging: boolean): React.CSSProperties => ({
    border: `2px dashed ${dragging ? "var(--accent, #1E40AF)" : "var(--border-strong, #C7C7BF)"}`,
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-4, 32px) var(--space-2, 16px)",
    textAlign: "center",
    cursor: "pointer",
    background: dragging ? "#EEF2FF" : "#FAFAFA",
    transition: "all 0.2s",
    marginBottom: "var(--space-2, 16px)",
  }),

  uploadIcon: {
    fontSize: 32,
    marginBottom: 8,
    color: "var(--muted, #6B6B66)",
  } as React.CSSProperties,

  uploadText: {
    fontSize: 14,
    color: "var(--muted, #6B6B66)",
    margin: 0,
  } as React.CSSProperties,

  uploadHint: {
    fontSize: 12,
    color: "var(--muted, #6B6B66)",
    margin: "4px 0 0",
  } as React.CSSProperties,

  fileInput: {
    display: "none",
  } as React.CSSProperties,

  /* ── Preview ── */
  previewRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 14px",
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    marginBottom: "var(--space-2, 16px)",
  } as React.CSSProperties,

  previewName: {
    flex: 1,
    fontSize: 14,
    fontWeight: 500,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as React.CSSProperties,

  previewSize: {
    fontSize: 12,
    color: "var(--muted, #6B6B66)",
  } as React.CSSProperties,

  removeBtn: {
    background: "none",
    border: "none",
    color: "var(--danger, #B91C1C)",
    cursor: "pointer",
    fontSize: 18,
    lineHeight: 1,
    padding: "4px 8px",
  } as React.CSSProperties,

  /* ── Content panel ── */
  contentPanel: {
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-2, 16px)",
    minHeight: 80,
  } as React.CSSProperties,

  sectionTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: 18,
    fontWeight: 500,
    margin: "20px 0 10px",
  } as React.CSSProperties,

  bodyText: {
    fontSize: 15,
    lineHeight: 1.7,
    color: "var(--fg, #1A1A1A)",
    margin: "0 0 12px",
  } as React.CSSProperties,

  /* ── Cards ── */
  redCard: {
    background: "#FFEBEE",
    border: "1px solid #EF5350",
    borderRadius: "var(--radius, 4px)",
    padding: "10px 12px",
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 1.5,
  } as React.CSSProperties,

  amberCard: {
    background: "#FFF8E1",
    border: "1px solid #FFC107",
    borderRadius: "var(--radius, 4px)",
    padding: "10px 12px",
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 1.5,
  } as React.CSSProperties,

  greenCard: {
    background: "#E8F5E9",
    border: "1px solid #4CAF50",
    borderRadius: "var(--radius, 4px)",
    padding: "10px 12px",
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 1.5,
  } as React.CSSProperties,

  chargeCard: {
    background: "#F5F7FA",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    marginBottom: 8,
    overflow: "hidden",
  } as React.CSSProperties,

  chargeHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 14px",
    cursor: "pointer",
    userSelect: "none",
    fontSize: 14,
    fontWeight: 500,
    background: "#EEF2FF",
  } as React.CSSProperties,

  chargeBody: {
    padding: "10px 14px",
    fontSize: 14,
    lineHeight: 1.6,
    borderTop: "1px solid var(--border, #E5E5E0)",
  } as React.CSSProperties,

  /* ── Accordion arrow ── */
  arrow: (open: boolean): React.CSSProperties => ({
    display: "inline-block",
    transition: "transform 0.2s",
    transform: open ? "rotate(90deg)" : "rotate(0deg)",
    fontSize: 12,
    color: "var(--muted, #6B6B66)",
  }),

  /* ── Boolean badges ── */
  badgeTrue: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: "var(--radius, 4px)",
    fontSize: 13,
    fontWeight: 500,
    background: "#E8F5E9",
    color: "#2E7D32",
  } as React.CSSProperties,

  badgeFalse: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: "var(--radius, 4px)",
    fontSize: 13,
    fontWeight: 500,
    background: "#FFEBEE",
    color: "#C62828",
  } as React.CSSProperties,

  badgeUnknown: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: "var(--radius, 4px)",
    fontSize: 13,
    fontWeight: 500,
    background: "#F5F5F5",
    color: "var(--muted, #6B6B66)",
  } as React.CSSProperties,

  /* ── Party chips ── */
  chipRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 12,
  } as React.CSSProperties,

  chip: {
    background: "#E8EAF6",
    color: "var(--accent, #1E40AF)",
    fontSize: 13,
    padding: "4px 12px",
    borderRadius: "var(--radius, 4px)",
    fontWeight: 500,
  } as React.CSSProperties,

  disclaimer: {
    marginTop: "var(--space-3, 24px)",
    padding: "var(--space-2, 16px)",
    background: "#f5f5f5",
    borderLeft: "3px solid var(--muted, #6B6B66)",
    fontSize: 12,
    lineHeight: 1.6,
    color: "var(--muted, #6B6B66)",
  } as React.CSSProperties,

  loadingPulse: {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "var(--accent, #1E40AF)",
    animation: "pulse 1s infinite",
    marginLeft: 4,
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PoliceReportAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [response, setResponse] = useState<Partial<AnalysisResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCharges, setExpandedCharges] = useState<Set<number>>(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Language is read from the ?language= query param (en/es), matching the
  // other explainer pages. Defaults to English.
  const [sp] = useSearchParams();
  const language = (sp.get("language") as "en" | "es") || "en";

  // ── Drag & drop handlers ──────────────────────────────────────────
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragging(false), []);

  const handleFilePick = useCallback(() => inputRef.current?.click(), []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  }, []);

  const removeFile = useCallback(() => {
    setFile(null);
    setResponse({});
    setError(null);
  }, []);

  // ── Analyze ───────────────────────────────────────────────────────
  const analyze = useCallback(async () => {
    if (!file) return;
    setStreaming(true);
    setError(null);
    setResponse({});

    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
    const fd = new FormData();
    fd.append("file", file);
    fd.append("language", language);

    try {
      const res = await fetch(`${base}/api/police-report/analyze`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      let receivedAnalysis = false;
      let errorReceived = false;
      for await (const { event, data: chunk } of readSSE(reader)) {
        if (event === "error") {
          errorReceived = true;
          try {
            const parsed = JSON.parse(chunk) as { message?: string };
            setError(
              parsed.message || "Analysis could not be completed. Please try again.",
            );
          } catch {
            setError("Analysis could not be completed. Please try again.");
          }
          break;
        }
        if (event === "progress") {
          continue; // heartbeat — the fixed "Analyzing report" state stays
        }
        if (event === "disclaimer") {
          try {
            const parsed = JSON.parse(chunk);
            setResponse((prev) => ({ ...prev, disclaimer: parsed.disclaimer ?? chunk }));
          } catch {
            setResponse((prev) => ({ ...prev, disclaimer: chunk }));
          }
          continue;
        }

        // Every remaining frame is a complete typed payload (Phase A
        // protocol). Unknown events are logged and ignored, never rendered.
        try {
          const solo = JSON.parse(chunk);
          if (event === "analysis_json") {
            receivedAnalysis = true;
            setResponse((prev) =>
              applySseEvent(prev, { type: "analysis_json", data: solo }),
            );
          } else if (event === "risk_analysis" && solo.type === "risk_analysis") {
            setResponse((prev) => applySseEvent(prev, solo));
          } else if (
            event === "relevant_opinions" &&
            solo.type === "relevant_opinions"
          ) {
            setResponse((prev) =>
              applySseEvent(prev, solo as RelevantOpinionsEvent),
            );
          } else if (event === "case_context" && solo.type === "case_context") {
            setResponse((prev) => applySseEvent(prev, solo));
          } else {
            console.debug(`[SSE] ignoring unknown event type: ${event}`);
          }
        } catch {
          console.debug(`[SSE] unparseable payload on event: ${event}`);
        }
      }

      if (!receivedAnalysis && !errorReceived) {
        setError("No response received. Please try again.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setStreaming(false);
    }
  }, [file, language]);

  // ── Toggle charge expansion ───────────────────────────────────────
  const toggleCharge = (i: number) => {
    setExpandedCharges((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div style={css.page}>
      <header style={css.header}>
        <Link to="/" style={css.backLink}>
          ← Back to LegalClear
        </Link>
        <h1 style={css.title}>Police Report Analyzer</h1>
        <p style={css.subtitle}>
          Upload a Florida police report for plain-English analysis
        </p>
      </header>

      {/* Upload zone */}
      {!file && (
        <div
          style={css.uploadZone(dragging)}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleFilePick}
        >
          <div style={css.uploadIcon}>📄</div>
          <p style={css.uploadText}>
            Drop a police report here or tap to upload
          </p>
          <p style={css.uploadHint}>PDF, JPG, PNG — up to 15 MB</p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.gif,.webp"
            style={css.fileInput}
            onChange={handleChange}
          />
        </div>
      )}

      {/* File preview + analyze button */}
      {file && (
        <>
          <div style={css.previewRow}>
            <span style={{ fontSize: 20 }}>📎</span>
            <span style={css.previewName}>{file.name}</span>
            <span style={css.previewSize}>{formatSize(file.size)}</span>
            <button style={css.removeBtn} onClick={removeFile} title="Remove">
              ×
            </button>
          </div>
          {!streaming && !response.incident_summary && (
            <button
              onClick={analyze}
              style={{
                display: "block",
                width: "100%",
                padding: "12px 0",
                background: "var(--accent, #1E40AF)",
                color: "#fff",
                border: "none",
                borderRadius: "var(--radius, 4px)",
                fontSize: 15,
                fontWeight: 500,
                cursor: "pointer",
                marginBottom: "var(--space-2, 16px)",
              }}
            >
              Analyze Report
            </button>
          )}
        </>
      )}

      {/* Analysis results */}
            {response.case_context?.routing && (
              <CaseContextBanner caseContext={response.case_context} />
            )}
      <div style={css.contentPanel}>
        {error && (
          <p style={{ color: "var(--danger, #B91C1C)", fontSize: 14 }}>
            {error}
          </p>
        )}

        {streaming && !response.incident_summary && (
          <p style={{ color: "var(--muted)", fontSize: 14, fontStyle: "italic" }}>
            Analyzing report
            <span style={css.loadingPulse} />
          </p>
        )}

        {response.incident_summary && (
          <>
            {/* Incident summary */}
            <h2 style={css.sectionTitle}>Incident Summary</h2>
            <p style={css.bodyText}>{response.incident_summary}</p>

            {/* Parties */}
            {response.parties && response.parties.length > 0 && (
              <>
                <h2 style={css.sectionTitle}>Parties Listed</h2>
                <div style={css.chipRow}>
                  {response.parties.map((p, i) => (
                    <span key={i} style={css.chip}>{p}</span>
                  ))}
                </div>
              </>
            )}

            {/* Charges explained — expandable */}
            {response.charges_explained &&
              response.charges_explained.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Charges & Violations</h2>
                  {response.charges_explained.map((c, i) => {
                    const open = expandedCharges.has(i);
                    return (
                      <div key={i} style={css.chargeCard}>
                        <div
                          style={css.chargeHeader}
                          onClick={() => toggleCharge(i)}
                        >
                          <span>{c.charge}</span>
                          <span style={css.arrow(open)}>▶</span>
                        </div>
                        {open && (
                          <div style={css.chargeBody}>
                            {c.plain_english}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </>
              )}

            {/* Miranda rights */}
            <h2 style={css.sectionTitle}>Miranda Rights</h2>
            {response.miranda_noted === true && (
              <span style={css.badgeTrue}>✓ Noted as read</span>
            )}
            {response.miranda_noted === false && (
              <span style={css.badgeFalse}>✗ Not noted</span>
            )}
            {response.miranda_noted === null && (
              <span style={css.badgeUnknown}>Not indicated in report</span>
            )}

            {/* Probable cause */}
            <h2 style={css.sectionTitle}>Probable Cause</h2>
            {response.probable_cause_present === true && (
              <>
                <span style={css.badgeTrue}>✓ Statement present</span>
                {response.probable_cause_summary && (
                  <p style={{ ...css.bodyText, marginTop: 8 }}>
                    {response.probable_cause_summary}
                  </p>
                )}
              </>
            )}
            {response.probable_cause_present === false && (
              <span style={css.badgeFalse}>✗ No probable cause statement</span>
            )}
            {response.probable_cause_present === null && (
              <span style={css.badgeUnknown}>Cannot determine from report</span>
            )}

            {/* ── Risk Analysis Card ── */}
            {response.risk_analysis && (
              <RiskScoreCard risk={response.risk_analysis} />
            )}

            {/* Discrepancies — cards with severity badges */}
            {response.discrepancies &&
              response.discrepancies.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>
                    Discrepancies & Inconsistencies
                  </h2>
                  {response.discrepancies.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        border: "1px solid var(--border, #E5E5E0)",
                        borderRadius: "var(--radius, 4px)",
                        padding: 14,
                        marginBottom: 10,
                        background:
                          d.severity === "high"
                            ? "#FFEBEE"
                            : d.severity === "medium"
                              ? "#FFF8E1"
                              : "#FAFAFA",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          justifyContent: "space-between",
                          marginBottom: 8,
                        }}
                      >
                        <SeverityBadge severity={d.severity} />
                        {d.page_ref && (
                          <span
                            style={{
                              fontSize: 11,
                              color: "var(--muted)",
                              fontFamily: "monospace",
                            }}
                          >
                            {d.page_ref}
                          </span>
                        )}
                      </div>
                      <p
                        style={{
                          margin: "0 0 8px",
                          fontSize: 14,
                          lineHeight: 1.6,
                        }}
                      >
                        {d.description}
                      </p>
                      {d.ask_attorney && (
                        <div
                          style={{
                            border: "1px solid var(--border, #E5E5E0)",
                            padding: 10,
                            background: "var(--bg-elevated, #fafafa)",
                            borderRadius: "var(--radius, 4px)",
                          }}
                        >
                          <p
                            style={{
                              margin: "0 0 4px",
                              fontSize: 11,
                              color: "var(--muted)",
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                            }}
                          >
                            Ask Your Attorney About
                          </p>
                          <p
                            style={{
                              margin: 0,
                              fontSize: 13,
                              lineHeight: 1.5,
                            }}
                          >
                            {d.ask_attorney}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </>
              )}

            {/* Missing fields — cards with severity badges */}
            {response.missing_fields &&
              response.missing_fields.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Missing Fields</h2>
                  {response.missing_fields.map((m, i) => (
                    <div
                      key={i}
                      style={{
                        border: "1px solid var(--border, #E5E5E0)",
                        borderRadius: "var(--radius, 4px)",
                        padding: 14,
                        marginBottom: 10,
                        background:
                          m.severity === "high"
                            ? "#FFEBEE"
                            : m.severity === "medium"
                              ? "#FFF8E1"
                              : "#FAFAFA",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          justifyContent: "space-between",
                          marginBottom: 8,
                        }}
                      >
                        <SeverityBadge severity={m.severity} />
                        {m.page_ref && (
                          <span
                            style={{
                              fontSize: 11,
                              color: "var(--muted)",
                              fontFamily: "monospace",
                            }}
                          >
                            {m.page_ref}
                          </span>
                        )}
                      </div>
                      <p
                        style={{
                          fontWeight: 500,
                          margin: "0 0 4px",
                          fontSize: 14,
                        }}
                      >
                        {m.field_name}
                      </p>
                      <p
                        style={{
                          margin: 0,
                          fontSize: 13,
                          lineHeight: 1.5,
                          color: "var(--muted)",
                        }}
                      >
                        {m.why_important}
                      </p>
                    </div>
                  ))}
                </>
              )}

            {/* Citation checks — deterministic verification, educational
                framing (AGENTS.md 2b): every statute citation was checked
                against the Florida Statutes before it reached the user. */}
            {response.citations_checked &&
              response.citations_checked.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Citations Checked</h2>
                  <div
                    style={{
                      border: "1px solid var(--border, #E5E5E0)",
                      borderRadius: "var(--radius, 4px)",
                      padding: 14,
                      marginBottom: 10,
                      background: "#FAFAFA",
                    }}
                  >
                    <p
                      style={{
                        fontSize: 12,
                        color: "var(--muted)",
                        margin: "0 0 10px",
                        lineHeight: 1.5,
                      }}
                    >
                      Every statute citation in this analysis was checked
                      against the Florida Statutes before you saw it.
                      Citations that could not be verified were removed.
                    </p>
                    {response.citations_checked.map((c, i) => {
                      const scrubbed = c.status.startsWith("scrubbed_");
                      const verified = c.status === "verified";
                      return (
                        <div
                          key={i}
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            alignItems: "center",
                            gap: 8,
                            fontSize: 13,
                            marginBottom: 6,
                            lineHeight: 1.5,
                          }}
                        >
                          <span
                            style={{
                              color: scrubbed
                                ? "var(--danger, #B91C1C)"
                                : verified
                                  ? "#1B873B"
                                  : "var(--muted)",
                              fontWeight: 600,
                            }}
                          >
                            {scrubbed ? "✗ removed" : verified ? "✓" : "ℹ"}
                          </span>
                          <span>{c.citation}</span>
                          {verified && c.adjudication === "SUPPORTED" && (
                            <span
                              style={{ color: "#1B873B", fontSize: 12 }}
                            >
                              — supported by the statute text
                            </span>
                          )}
                          {verified && c.adjudication === "unavailable" && (
                            <span
                              style={{
                                color: "var(--muted)",
                                fontSize: 12,
                              }}
                            >
                              — checked against the Florida Statutes
                            </span>
                          )}
                          {c.status === "from_report" && (
                            <span
                              style={{
                                color: "var(--muted)",
                                fontSize: 12,
                              }}
                            >
                              — cited from your report
                            </span>
                          )}
                        </div>
                      );
                    })}
                    {(response.citation_notes || []).map((note, i) => (
                      <p
                        key={i}
                        style={{
                          margin: "6px 0 0",
                          fontSize: 12,
                          lineHeight: 1.5,
                          color: "var(--muted)",
                        }}
                      >
                        {note}
                      </p>
                    ))}
                  </div>
                </>
              )}

            {/* Relevant Florida case law — retrieved by situation-tag overlap.
                Three states: (1) opinions found → cards; (2) defect tags
                derived but no corpus match → explicit "ask your attorney"
                message (never a silent empty section); (3) no tags derived
                → section omitted entirely. */}
            {(() => {
              const tags = response.situation_tags_used ?? [];
              const opinions = response.relevant_opinions ?? [];

              if (opinions.length > 0) {
                return (
                  <>
                    <h2 style={css.sectionTitle}>Relevant Florida Case Law</h2>
                    {opinions.map((op, i) => (
                      <OpinionCard
                        key={op.citation || i}
                        opinion={op}
                        language={language}
                      />
                    ))}
                  </>
                );
              }

              if (tags.length > 0) {
                return (
                  <>
                    <h2 style={css.sectionTitle}>Relevant Florida Case Law</h2>
                    <p style={css.bodyText}>
                      No matching Florida case law in our database yet for
                      this issue — ask your attorney directly.
                    </p>
                  </>
                );
              }

              return null;
            })()}

            {/* What happens next */}
            <h2 style={css.sectionTitle}>What Typically Happens Next</h2>
            <p style={css.bodyText}>{response.what_happens_next}</p>
          </>
        )}
      </div>

      {/* Disclaimer */}
      <div style={css.disclaimer}>
        {response.disclaimer || DISCLAIMER_TEXT}
      </div>

      <ChatButton module="police_report" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer module="police_report" onClose={() => setChatOpen(false)} />
      )}
    </div>
  );
}
