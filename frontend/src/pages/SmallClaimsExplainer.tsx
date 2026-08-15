/**
 * Module 1 — Small Claims Explainer page.
 *
 * Mobile-first two-panel layout:
 *   Top panel — situation summary card (entities from intake)
 *   Bottom panel — streaming AI explanation via SSE
 *
 * Third-person framing, disclaimer on every render.
 */

import { useState, useRef, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";
import { parseDisclaimerPayload, readSSE } from "../lib/sse";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExplainResponse {
  what_this_is: string;
  what_usually_happens: string;
  typical_timeline: string;
  useful_documentation: string[];
  watch_out_for: string[];
  typical_outcomes: string[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Helper — read SSE stream
// ---------------------------------------------------------------------------

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

  /* ── Top panel — summary card ── */
  summaryCard: {
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-2, 16px)",
    marginBottom: "var(--space-2, 16px)",
  } as React.CSSProperties,

  summaryTitle: {
    fontFamily: "var(--font-sans)",
    fontSize: 11,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--muted, #6B6B66)",
    margin: "0 0 12px",
  } as React.CSSProperties,

  entityRow: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 14,
    lineHeight: 1.7,
    borderBottom: "1px solid var(--border, #E5E5E0)",
    padding: "6px 0",
  } as React.CSSProperties,

  entityKey: {
    color: "var(--muted, #6B6B66)",
    textTransform: "capitalize",
  } as React.CSSProperties,

  entityVal: {
    fontWeight: 500,
    textAlign: "right",
    maxWidth: "60%",
    wordBreak: "break-word",
  } as React.CSSProperties,

  /* ── Bottom panel — streaming ── */
  streamPanel: {
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-2, 16px)",
    minHeight: 120,
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

  /* ── Card lists ── */
  docList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
  } as React.CSSProperties,

  docItem: {
    padding: "8px 0",
    borderBottom: "1px solid var(--border, #E5E5E0)",
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

  disclaimer: {
    marginTop: "var(--space-3, 24px)",
    padding: "var(--space-2, 16px)",
    background: "#f5f5f5",
    borderLeft: "3px solid var(--muted, #6B6B66)",
    fontSize: 12,
    lineHeight: 1.6,
    color: "var(--muted, #6B6B66)",
  } as React.CSSProperties,

  fileLink: {
    display: "inline-block",
    marginTop: "var(--space-2, 16px)",
    padding: "10px 20px",
    background: "var(--accent, #1E40AF)",
    color: "#fff",
    textDecoration: "none",
    borderRadius: "var(--radius, 4px)",
    fontSize: 14,
    fontWeight: 500,
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

  /* ── Input form (P2.0-B) — mirrors PropertyCasualtyExplainer ── */
  inputSection: {
    background: "#fff",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    padding: "var(--space-2, 16px)",
    marginBottom: "var(--space-2, 16px)",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  } as React.CSSProperties,

  textarea: {
    width: "100%",
    minHeight: 120,
    padding: "12px",
    fontSize: 16,
    lineHeight: 1.6,
    fontFamily: "var(--font-sans)",
    background: "#fff",
    color: "var(--fg, #1A1A1A)",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    boxSizing: "border-box",
    outline: "none",
    resize: "vertical",
  } as React.CSSProperties,

  textInput: {
    width: "100%",
    minHeight: 48,
    padding: "10px 12px",
    fontSize: 16,
    background: "#fff",
    color: "var(--fg, #1A1A1A)",
    border: "1px solid var(--border, #E5E5E0)",
    borderRadius: "var(--radius, 4px)",
    boxSizing: "border-box",
    outline: "none",
  } as React.CSSProperties,

  submitBtn: {
    display: "block",
    width: "100%",
    minHeight: 48,
    padding: "0 16px",
    background: "var(--accent, #1E40AF)",
    color: "#fff",
    border: "none",
    borderRadius: "var(--radius, 4px)",
    fontSize: 15,
    fontWeight: 500,
    cursor: "pointer",
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SmallClaimsExplainer() {
  const [searchParams] = useSearchParams();
  const [response, setResponse] = useState<Partial<ExplainResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rawChunks, setRawChunks] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [claimDescription, setClaimDescription] = useState("");
  const [claimAmount, setClaimAmount] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const language = (searchParams.get("language") as "en" | "es") || "en";

  // ── Start streaming on mount ───────────────────────────────────────
  const startStream = useCallback(async () => {
    setStreaming(true);
    setError(null);
    setRawChunks("");
    setResponse({});

    const controller = new AbortController();
    abortRef.current = controller;

    // Form inputs are the source of truth (P2.0-B).
    const entities: Record<string, string> = {
      claim_description: claimDescription,
      claim_amount: claimAmount,
    };

    const base = import.meta.env.VITE_API_URL || "http://localhost:8001";

    try {
      const res = await fetch(`${base}/api/small-claims/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": import.meta.env.VITE_API_KEY,
        },
        body: JSON.stringify({ entities, language }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      let full = "";
      for await (const { event, data: chunk } of readSSE(reader)) {
        if (event === "disclaimer") {
          setResponse((p) => ({ ...p, disclaimer: parseDisclaimerPayload(chunk) }));
          continue;
        }
        if (event !== "message") {
          console.debug(`[SSE] ignoring unknown event type: ${event}`);
          continue;
        }
        full += chunk;
        setRawChunks(full);

        // Try to parse partial JSON — if it fails we just keep streaming
        try {
          const parsed = JSON.parse(full);
          setResponse(parsed as ExplainResponse);
        } catch {
          // Partial JSON, keep accumulating
        }
      }

      // Final parse
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
  }, [claimDescription, claimAmount, language]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = () => {
    if (!claimDescription.trim()) return;
    setSubmitted(true);
    startStream();
  };

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div style={css.page}>
      {/* Header */}
      <header style={css.header}>
        <Link to="/" style={css.backLink}>
          ← Back to LegalClear
        </Link>
        <h1 style={css.title}>Small Claims Court</h1>
        <p style={css.subtitle}>Florida county court — disputes up to $8,000</p>
      </header>

      {/* Input form — source of truth (P2.0-B). Shown until explicit submit. */}
      {!submitted && (
        <div style={css.inputSection}>
          <textarea
            style={css.textarea}
            value={claimDescription}
            onChange={(e) => setClaimDescription(e.target.value)}
            placeholder="Describe your small claims situation in detail..."
            rows={5}
          />
          <input
            style={css.textInput}
            type="text"
            value={claimAmount}
            onChange={(e) => setClaimAmount(e.target.value)}
            placeholder="Claim amount (e.g. $2,500)"
          />
          <button
            style={css.submitBtn}
            onClick={handleSubmit}
            disabled={!claimDescription.trim()}
          >
            Analyze My Situation
          </button>
        </div>
      )}

      {/* Disclaimer — always visible: below the submit button, above any LLM output */}
      <div style={css.disclaimer}>
        {response.disclaimer ||
          "LegalClear provides legal information, not legal advice."}
      </div>

      {/* Results — streaming response, only after explicit submit */}
      {submitted && (
        <div style={css.streamPanel}>
        {error && (
          <p style={{ color: "var(--danger, #B91C1C)", fontSize: 14 }}>
            {error}
          </p>
        )}

        {streaming && !response.what_this_is && (
          <p style={css.streamPlaceholder}>
            Generating explanation
            <span style={css.loadingPulse} />
          </p>
        )}

        {/* Structured output once available */}
        {response.what_this_is && (
          <>
            <h2 style={css.sectionTitle}>What This Is</h2>
            <p style={css.bodyText}>{response.what_this_is}</p>

            <h2 style={css.sectionTitle}>What Usually Happens</h2>
            <p style={css.bodyText}>{response.what_usually_happens}</p>

            <h2 style={css.sectionTitle}>Typical Timeline</h2>
            <p style={css.bodyText}>{response.typical_timeline}</p>

            {response.useful_documentation &&
              response.useful_documentation.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Useful Documentation</h2>
                  <ul style={css.docList}>
                    {response.useful_documentation.map((doc, i) => (
                      <li key={i} style={css.docItem}>
                        {doc}
                      </li>
                    ))}
                  </ul>
                </>
              )}

            {response.watch_out_for &&
              response.watch_out_for.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Watch Out For</h2>
                  {response.watch_out_for.map((w, i) => (
                    <div key={i} style={css.amberCard}>
                      ⚠ {w}
                    </div>
                  ))}
                </>
              )}

            {response.typical_outcomes &&
              response.typical_outcomes.length > 0 && (
                <>
                  <h2 style={css.sectionTitle}>Typical Outcomes</h2>
                  {response.typical_outcomes.map((o, i) => (
                    <div key={i} style={css.greenCard}>
                      ✓ {o}
                    </div>
                  ))}
                </>
              )}

            {/* Filing wizard link */}
            <Link
              to="/small-claims/file"
              style={css.fileLink}
            >
              Ready to file? Start the Small Claims Wizard →
            </Link>
          </>
        )}

        {/* Raw streaming fallback when JSON hasn't parsed yet but we have chunks */}
        {streaming && rawChunks && !response.what_this_is && (
          <p style={{ ...css.bodyText, color: "var(--muted)" }}>
            {rawChunks.slice(0, 300)}…
          </p>
        )}
      </div>
      )}

      {/* Chat system */}
      <ChatButton module="small_claims" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer module="small_claims" onClose={() => setChatOpen(false)} />
      )}
    </div>
  );
}
