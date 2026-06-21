/**
 * v3 Homepage — AI-first intake screen.
 *
 * Replaces the Phase 15 tile hub with a single textarea intake.
 * POST /api/intake → routes to the correct module page.
 * "unknown" modules show a clarifying question inline.
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import HubTile from "../components/HubTile";

// ---------------------------------------------------------------------------
// Module tile definitions (secondary nav)
// ---------------------------------------------------------------------------

const MODULE_TILES = [
  { title: "Small Claims", subtitle: "Disputes up to $8,000", to: "/small-claims" },
  { title: "Criminal", subtitle: "Procedure explained by stage", to: "/criminal-procedure" },
  { title: "Police Report", subtitle: "Upload and analyze", to: "/police-report" },
  { title: "Discovery", subtitle: "Motion analysis under Rule 3.220", to: "/discovery-motion" },
  { title: "Property & Casualty", subtitle: "Insurance and liability", to: "/property-casualty" },
  { title: "Forms", subtitle: "Find Florida court forms", to: "/forms" },
];

// ---------------------------------------------------------------------------
// Route mapping from intake module → frontend route
// ---------------------------------------------------------------------------

function buildRoute(module: string, entities: Record<string, unknown>, language: string): string {
  const params = new URLSearchParams();
  params.set("language", language);
  for (const [k, v] of Object.entries(entities)) {
    if (v !== null && v !== undefined) {
      params.set(k, String(v));
    }
  }

  switch (module) {
    case "small_claims":
      return `/small-claims?${params.toString()}`;
    case "criminal_procedure":
      return `/criminal-procedure?${params.toString()}`;
    case "police_report":
      return `/police-report?${params.toString()}`;
    case "discovery_motion":
      return `/discovery-motion?${params.toString()}`;
    case "property_casualty":
      return `/property-casualty?${params.toString()}`;
    default:
      return "";
  }
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  page: { maxWidth: 680, margin: "0 auto", padding: "var(--space-2)" } as React.CSSProperties,

  /* ── Hero ── */
  hero: { padding: "var(--space-6) 0 var(--space-3)" } as React.CSSProperties,
  wordmark: { fontFamily: "var(--font-serif)", fontSize: 36, fontWeight: 500,
    letterSpacing: "-0.025em", lineHeight: 1.1, margin: "0 0 var(--space-1)" } as React.CSSProperties,
  subhead: { fontSize: 16, lineHeight: 1.55, color: "var(--muted)", margin: "0 0 var(--space-3)" } as React.CSSProperties,

  /* ── Language toggle ── */
  langRow: { display: "flex", justifyContent: "flex-end", marginBottom: "var(--space-1)" } as React.CSSProperties,
  langBtn: (active: boolean): React.CSSProperties => ({
    background: "none", border: active ? "2px solid var(--accent)" : "2px solid transparent",
    borderRadius: "var(--radius)", padding: "4px 10px", fontSize: 13, fontWeight: active ? 600 : 400,
    color: active ? "var(--accent)" : "var(--muted)", cursor: "pointer", marginLeft: 4,
  }),

  /* ── Intake box ── */
  textarea: { width: "100%", minHeight: 140, padding: "var(--space-2)", fontSize: 16,
    lineHeight: 1.6, fontFamily: "var(--font-sans)", border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)", resize: "vertical", background: "#fff", color: "var(--fg)",
    boxSizing: "border-box" } as React.CSSProperties,
  btnRow: { display: "flex", justifyContent: "space-between", alignItems: "center",
    marginTop: "var(--space-1)" } as React.CSSProperties,
  submitBtn: { padding: "12px 28px", background: "var(--accent)", color: "#fff", border: "none",
    borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "pointer" } as React.CSSProperties,
  submitBtnDisabled: { padding: "12px 28px", background: "var(--border-strong)", color: "#fff", border: "none",
    borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "not-allowed" } as React.CSSProperties,

  /* ── Clarifying question ── */
  clarifyBox: { marginTop: "var(--space-2)", padding: "var(--space-2)", background: "#FFF8E1",
    border: "1px solid #FFC107", borderRadius: "var(--radius)", fontSize: 14, lineHeight: 1.6 } as React.CSSProperties,
  clarifyTitle: { fontWeight: 600, margin: "0 0 8px", fontSize: 13, textTransform: "uppercase",
    letterSpacing: "0.06em", color: "#795548" } as React.CSSProperties,
  clarifyText: { margin: 0, fontSize: 14, lineHeight: 1.6 } as React.CSSProperties,

  /* ── Error ── */
  error: { color: "var(--danger)", fontSize: 13, marginTop: 8 } as React.CSSProperties,

  /* ── Secondary nav ── */
  navSection: { paddingTop: "var(--space-4)" } as React.CSSProperties,
  navLabel: { fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em",
    color: "var(--muted)", margin: "0 0 var(--space-2)" } as React.CSSProperties,
  scrollRow: { display: "flex", gap: 10, overflowX: "auto", paddingBottom: 8,
    WebkitOverflowScrolling: "touch", scrollbarWidth: "none" } as React.CSSProperties,
  tileWrap: { flex: "0 0 180px" } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HomeHub() {
  const navigate = useNavigate();
  const [situation, setSituation] = useState("");
  const [language, setLanguage] = useState<"en" | "es">("en");
  const [loading, setLoading] = useState(false);
  const [clarify, setClarify] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    const trimmed = situation.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setClarify(null);

    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

    try {
      const res = await fetch(`${base}/api/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ situation: trimmed, language }),
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const data = await res.json();
      const module: string = data.module || "unknown";
      const entities: Record<string, unknown> = data.entities || {};

      if (module === "unknown") {
        setClarify(data.clarifying_question || "Could you share more about your situation?");
        setLoading(false);
        return;
      }

      // Add sub_type to entities if present
      if (data.sub_type) {
        entities.sub_type = data.sub_type;
      }

      // Navigate to the appropriate module
      const route = buildRoute(module, entities, language);
      if (route) {
        navigate(route);
      } else {
        setError("Could not determine the right page. Please try again.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [situation, language, navigate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div style={S.page}>
      {/* Hero */}
      <header style={S.hero}>
        <h1 style={S.wordmark}>LegalClear</h1>
        <p style={S.subhead}>Florida legal help, explained in plain English</p>
      </header>

      {/* Language toggle */}
      <div style={S.langRow}>
        <button style={S.langBtn(language === "en")} onClick={() => setLanguage("en")}>EN</button>
        <button style={S.langBtn(language === "es")} onClick={() => setLanguage("es")}>ES</button>
      </div>

      {/* Intake textarea */}
      <textarea
        style={S.textarea}
        value={situation}
        onChange={(e) => { setSituation(e.target.value); setClarify(null); setError(null); }}
        onKeyDown={handleKeyDown}
        placeholder={
          language === "es"
            ? "Describa su situación en lenguaje sencillo…"
            : "Describe your situation in plain English…"
        }
        disabled={loading}
      />

      {/* Submit row */}
      <div style={S.btnRow}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          {loading ? "Analyzing…" : ""}
        </span>
        <button
          style={situation.trim() && !loading ? S.submitBtn : S.submitBtnDisabled}
          onClick={handleSubmit}
          disabled={!situation.trim() || loading}
        >
          {loading ? "…" : "Get Explanation"}
        </button>
      </div>

      {/* Error */}
      {error && <p style={S.error}>{error}</p>}

      {/* Clarifying question — shown when module is "unknown" */}
      {clarify && (
        <div style={S.clarifyBox}>
          <p style={S.clarifyTitle}>Tell us a little more</p>
          <p style={S.clarifyText}>{clarify}</p>
        </div>
      )}

      {/* Secondary nav — horizontal scroll of module tiles */}
      <section style={S.navSection}>
        <p style={S.navLabel}>Or jump to a topic</p>
        <div style={S.scrollRow}>
          {MODULE_TILES.map((t) => (
            <div key={t.to} style={S.tileWrap}>
              <HubTile title={t.title} subtitle={t.subtitle} to={t.to} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
