/**
 * Module 2 — Criminal Procedure Explainer page.
 *
 * Mobile-first layout with:
 *   - Stage progress bar (Arrested → … → Sentencing), current stage highlighted
 *   - Streaming AI explanation via SSE below the progress bar
 *   - next_stages rendered as sequential cards
 *
 * Third-person framing, disclaimer on every render.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NextStage {
  stage: string;
  what_happens: string;
  typical_duration: string;
}

interface ExplainResponse {
  current_stage_explanation: string;
  next_stages: NextStage[];
  typical_timeline: string;
  key_people_involved: string[];
  what_usually_happens: string;
  typical_outcomes: string[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STAGES = [
  "Arrested",
  "Charged",
  "Arraigned",
  "Pretrial",
  "Trial",
  "Sentencing",
];

// ---------------------------------------------------------------------------
// SSE reader
// ---------------------------------------------------------------------------

async function* readSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<string, void, unknown> {
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        yield line.slice(6);
      }
    }
  }
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

  /* ── Progress bar ── */
  progressContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-2, 16px) 0",
    overflow: "hidden",
    flexWrap: "nowrap",
    gap: 2,
  } as React.CSSProperties,

  stageDot: (active: boolean, past: boolean): React.CSSProperties => ({
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flex: "1 0 auto",
    minWidth: 0,
    position: "relative",
    opacity: past || active ? 1 : 0.45,
    transition: "opacity 0.3s",
  }),

  dotCircle: (active: boolean): React.CSSProperties => ({
    width: active ? 14 : 10,
    height: active ? 14 : 10,
    borderRadius: "50%",
    background: active
      ? "var(--accent, #1E40AF)"
      : "var(--border-strong, #C7C7BF)",
    transition: "all 0.3s",
  }),

  stageLabel: {
    fontSize: 9,
    textAlign: "center",
    color: "var(--muted, #6B6B66)",
    marginTop: 6,
    whiteSpace: "nowrap",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  } as React.CSSProperties,

  stageLabelActive: {
    fontSize: 9,
    textAlign: "center",
    color: "var(--accent, #1E40AF)",
    marginTop: 6,
    fontWeight: 600,
    whiteSpace: "nowrap",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  } as React.CSSProperties,

  /* ── Content panel ── */
  contentPanel: {
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-2, 16px)",
    minHeight: 120,
    marginTop: "var(--space-2, 16px)",
  } as React.CSSProperties,

  streamPlaceholder: {
    color: "var(--muted, #6B6B66)",
    fontSize: 14,
    fontStyle: "italic",
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

  /* ── Stage cards ── */
  stageCard: {
    background: "#F5F7FA",
    border: "1px solid var(--border, #E5E5E0)",
    borderLeft: "4px solid var(--accent, #1E40AF)",
    borderRadius: "var(--radius, 4px)",
    padding: "12px 14px",
    marginBottom: 12,
  } as React.CSSProperties,

  stageCardTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: 16,
    fontWeight: 500,
    margin: "0 0 4px",
    color: "var(--accent, #1E40AF)",
  } as React.CSSProperties,

  stageCardDuration: {
    fontSize: 12,
    color: "var(--muted, #6B6B66)",
    marginBottom: 8,
    fontStyle: "italic",
  } as React.CSSProperties,

  stageCardBody: {
    fontSize: 14,
    lineHeight: 1.6,
    color: "var(--fg, #1A1A1A)",
  } as React.CSSProperties,

  /* ── People chips ── */
  peopleRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 12,
  } as React.CSSProperties,

  personChip: {
    background: "#E8EAF6",
    color: "var(--accent, #1E40AF)",
    fontSize: 13,
    padding: "4px 12px",
    borderRadius: "var(--radius, 4px)",
    fontWeight: 500,
  } as React.CSSProperties,

  /* ── Outcome cards ── */
  outcomeCard: {
    background: "#E8F5E9",
    border: "1px solid #4CAF50",
    borderRadius: "var(--radius, 4px)",
    padding: "10px 12px",
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 1.5,
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

function stageIndex(stage: string): number {
  const idx = STAGES.findIndex(
    (s) => s.toLowerCase() === stage.toLowerCase(),
  );
  return idx >= 0 ? idx : -1;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CriminalProcedureExplainer() {
  const [searchParams] = useSearchParams();

  const chargeType = searchParams.get("charge_type") || "unknown charge";
  const severity = searchParams.get("severity") || "misdemeanor";
  const currentStage = searchParams.get("current_stage") || "arraigned";
  const language = (searchParams.get("language") as "en" | "es") || "en";

  const [response, setResponse] = useState<Partial<ExplainResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rawChunks, setRawChunks] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const currentIdx = stageIndex(currentStage);

  const startStream = useCallback(async () => {
    setStreaming(true);
    setError(null);
    setRawChunks("");
    setResponse({});

    const controller = new AbortController();
    abortRef.current = controller;

    const base = import.meta.env.VITE_API_URL || "http://localhost:8001";

    try {
      const res = await fetch(`${base}/api/criminal/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": import.meta.env.VITE_API_KEY || "testkey123",
        },
        body: JSON.stringify({
          charge_type: chargeType,
          severity,
          current_stage: currentStage,
          language,
        }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      let full = "";
      for await (const chunk of readSSE(reader)) {
        full += chunk;
        setRawChunks(full);
        try {
          const parsed = JSON.parse(full);
          setResponse(parsed as ExplainResponse);
        } catch {
          /* partial */
        }
      }

      try {
        const parsed = JSON.parse(full);
        setResponse(parsed as ExplainResponse);
      } catch {
        setError("Could not parse the explanation. Please try again.");
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred.",
      );
    } finally {
      setStreaming(false);
    }
  }, [chargeType, severity, currentStage, language]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    startStream();
    return () => abortRef.current?.abort();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div style={css.page}>
      {/* Header */}
      <header style={css.header}>
        <Link to="/" style={css.backLink}>
          ← Back to LegalClear
        </Link>
        <h1 style={css.title}>Criminal Procedure</h1>
        <p style={css.subtitle}>
          {chargeType} · {severity} · Florida courts
        </p>
      </header>

      {/* Stage progress bar */}
      <div style={css.progressContainer}>
        {STAGES.map((label, i) => {
          const past = currentIdx >= 0 && i < currentIdx;
          const active = i === currentIdx;
          return (
            <div key={label} style={css.stageDot(active, past)}>
              <div style={css.dotCircle(active)} />
              <span
                style={active ? css.stageLabelActive : css.stageLabel}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Streaming content */}
      <div style={css.contentPanel}>
        {error && (
          <p style={{ color: "var(--danger, #B91C1C)", fontSize: 14 }}>
            {error}
          </p>
        )}

        {streaming && !response.current_stage_explanation && (
          <p style={css.streamPlaceholder}>
            Generating explanation
            <span style={css.loadingPulse} />
          </p>
        )}

        {response.current_stage_explanation && (
          <>
            <h2 style={css.sectionTitle}>Current Stage: {currentStage}</h2>
            <p style={css.bodyText}>
              {response.current_stage_explanation}
            </p>

            <h2 style={css.sectionTitle}>What Usually Happens</h2>
            <p style={css.bodyText}>
              {response.what_usually_happens}
            </p>

            <h2 style={css.sectionTitle}>Typical Timeline</h2>
            <p style={css.bodyText}>{response.typical_timeline}</p>

            {response.key_people_involved &&
              response.key_people_involved.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Key People Involved</h2>
                  <div style={css.peopleRow}>
                    {response.key_people_involved.map((p, i) => (
                      <span key={i} style={css.personChip}>
                        {p}
                      </span>
                    ))}
                  </div>
                </>
              )}

            {response.next_stages &&
              response.next_stages.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Upcoming Stages</h2>
                  {response.next_stages.map((ns, i) => (
                    <div key={i} style={css.stageCard}>
                      <h3 style={css.stageCardTitle}>{ns.stage}</h3>
                      <p style={css.stageCardDuration}>
                        {ns.typical_duration}
                      </p>
                      <p style={css.stageCardBody}>
                        {ns.what_happens}
                      </p>
                    </div>
                  ))}
                </>
              )}

            {response.typical_outcomes &&
              response.typical_outcomes.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Typical Outcomes</h2>
                  {response.typical_outcomes.map((o, i) => (
                    <div key={i} style={css.outcomeCard}>
                      ✓ {o}
                    </div>
                  ))}
                </>
              )}
          </>
        )}

        {streaming && rawChunks && !response.current_stage_explanation && (
          <p style={{ ...css.bodyText, color: "var(--muted)" }}>
            {rawChunks.slice(0, 300)}…
          </p>
        )}
      </div>

      {/* Disclaimer */}
      <div style={css.disclaimer}>
        {response.disclaimer ||
          "LegalClear provides legal information, not legal advice. Nothing here creates an attorney-client relationship. Consult a licensed Florida attorney for your specific situation. If you cannot afford an attorney, you have the right to a public defender."}
      </div>

      <ChatButton module="criminal_procedure" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer module="criminal_procedure" onClose={() => setChatOpen(false)} />
      )}
    </div>
  );
}
