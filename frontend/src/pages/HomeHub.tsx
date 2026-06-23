/**
 * v3 Homepage — Modern Glossy AI-first intake screen.
 *
 * POST /api/intake → routes to the correct module page.
 * "unknown" modules show a clarifying question inline.
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import HubTile from "../components/HubTile";

// ---------------------------------------------------------------------------
// Brand tokens
// ---------------------------------------------------------------------------

const C = {
  navy: "#1a1a2e",
  blue: "#4361EE",
  purple: "#3A0CA3",
  grey: "#6B7280",
  border: "#E0E7FF",
  bgStart: "#F0F4FF",
  bgEnd: "#FAFAFA",
};

// ---------------------------------------------------------------------------
// Module tiles — with icons
// ---------------------------------------------------------------------------

const MODULE_TILES = [
  { title: "Small Claims", subtitle: "Disputes up to $8,000", to: "/small-claims", icon: "⚖️" },
  { title: "Criminal", subtitle: "Procedure explained by stage", to: "/criminal-procedure", icon: "🔒" },
  { title: "Police Report", subtitle: "Upload and analyze", to: "/police-report", icon: "📋" },
  { title: "Discovery", subtitle: "Motion analysis under Rule 3.220", to: "/discovery-motion", icon: "🔍" },
  { title: "Property & Casualty", subtitle: "Insurance and liability", to: "/property-casualty", icon: "🏠" },
  { title: "Wills & Trusts", subtitle: "Wills, trusts & probate explained", to: "/wills-trusts", icon: "📜" },
  { title: "Forms", subtitle: "Find Florida court forms", to: "/forms", icon: "📝" },
];

// ---------------------------------------------------------------------------
// Route mapping
// ---------------------------------------------------------------------------

function buildRoute(module: string, entities: Record<string, unknown>, language: string): string {
  const params = new URLSearchParams();
  params.set("language", language);
  for (const [k, v] of Object.entries(entities)) {
    if (v !== null && v !== undefined) params.set(k, String(v));
  }
  switch (module) {
    case "small_claims":      return `/small-claims?${params.toString()}`;
    case "criminal_procedure": return `/criminal-procedure?${params.toString()}`;
    case "police_report":     return `/police-report?${params.toString()}`;
    case "discovery_motion":  return `/discovery-motion?${params.toString()}`;
    case "property_casualty": return `/property-casualty?${params.toString()}`;
    case "wills_trusts":      return `/wills-trusts?${params.toString()}`;
    default: return "";
  }
}

// ---------------------------------------------------------------------------
// Inline styles
// ---------------------------------------------------------------------------

const S = {
  /* ── Full-page background wrapper ── */
  bg: {
    minHeight: "100%",
    background: `linear-gradient(180deg, ${C.bgStart} 0%, ${C.bgEnd} 100%)`,
  } as React.CSSProperties,

  /* ── Content column ── */
  page: {
    maxWidth: 800,
    margin: "0 auto",
    padding: "0 24px",
    display: "flex",
    flexDirection: "column",
    gap: 32,
  } as React.CSSProperties,

  /* ── Hero ── */
  hero: {
    paddingTop: 40,
    paddingBottom: 0,
  } as React.CSSProperties,

  wordmark: {
    fontFamily: "var(--font-serif)",
    fontSize: 48,
    fontWeight: 600,
    letterSpacing: "-0.025em",
    lineHeight: 1.05,
    margin: "0 0 8px",
  } as React.CSSProperties,

  subhead: {
    fontSize: 16,
    fontWeight: 400,
    color: C.grey,
    lineHeight: 1.4,
    margin: 0,
  } as React.CSSProperties,

  /* ── Language toggle — pill container ── */
  langContainer: {
    display: "flex",
    justifyContent: "flex-end",
  } as React.CSSProperties,

  langPill: {
    display: "inline-flex",
    background: C.bgStart,
    borderRadius: 10,
    padding: 4,
    gap: 2,
  } as React.CSSProperties,

  langBtn: (active: boolean): React.CSSProperties => ({
    background: active ? C.blue : "transparent",
    color: active ? "#fff" : C.grey,
    border: "none",
    borderRadius: 8,
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: active ? 600 : 400,
    cursor: "pointer",
    lineHeight: 1.2,
    transition: "background 0.15s, color 0.15s",
  }),

  /* ── Textarea ── */
  textarea: {
    width: "100%",
    minHeight: 120,
    padding: 20,
    fontSize: 16,
    lineHeight: 1.6,
    fontFamily: "var(--font-sans)",
    background: "#fff",
    color: C.navy,
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    boxShadow: "0 4px 24px rgba(67,97,238,0.08)",
    resize: "vertical",
    boxSizing: "border-box",
    outline: "none",
    transition: "border 0.2s, box-shadow 0.2s",
  } as React.CSSProperties,

  /* ── Button row ── */
  btnRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  } as React.CSSProperties,

  submitBtn: {
    padding: "14px 32px",
    background: `linear-gradient(135deg, ${C.blue} 0%, ${C.purple} 100%)`,
    color: "#fff",
    border: "none",
    borderRadius: 12,
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    lineHeight: 1.2,
    boxShadow: "0 4px 15px rgba(67,97,238,0.35)",
    transition: "box-shadow 0.2s, filter 0.2s",
  } as React.CSSProperties,

  submitBtnDisabled: {
    padding: "14px 32px",
    background: `linear-gradient(135deg, ${C.blue} 0%, ${C.purple} 100%)`,
    color: "#fff",
    border: "none",
    borderRadius: 12,
    fontSize: 15,
    fontWeight: 600,
    cursor: "not-allowed",
    lineHeight: 1.2,
    opacity: 0.5,
    boxShadow: "none",
  } as React.CSSProperties,

  /* ── Feedback ── */
  status: {
    fontSize: 12,
    color: C.grey,
  } as React.CSSProperties,

  error: {
    color: "var(--danger, #B91C1C)",
    fontSize: 13,
  } as React.CSSProperties,

  clarifyBox: {
    padding: 16,
    background: "#FFF8E1",
    border: "1px solid #FFC107",
    borderRadius: 12,
    fontSize: 14,
    lineHeight: 1.6,
  } as React.CSSProperties,

  clarifyTitle: {
    fontWeight: 600,
    margin: "0 0 4px",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.07em",
    color: "#795548",
  } as React.CSSProperties,

  clarifyText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.6,
  } as React.CSSProperties,

  /* ── Tile grid ── */
  navSection: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  } as React.CSSProperties,

  navLabel: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: C.grey,
    margin: 0,
  } as React.CSSProperties,

  tileGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 12,
  } as React.CSSProperties,

  /* ── Mobile overrides injected via inline media query style tag ── */
} as const;

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
  const [hoverBtn, setHoverBtn] = useState(false);

  const isEmpty = !situation.trim();

  const handleSubmit = useCallback(async () => {
    if (isEmpty) return;
    setLoading(true);
    setError(null);
    setClarify(null);

    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

    try {
      const res = await fetch(`${base}/api/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ situation: situation.trim(), language }),
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
      if (data.sub_type) entities.sub_type = data.sub_type;

      const route = buildRoute(module, entities, language);
      if (route) navigate(route);
      else setError("Could not determine the right page. Please try again.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [situation, language, isEmpty, navigate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <>
      {/* Mobile responsive overrides */}
      <style>{`
        @media (max-width: 480px) {
          .lc-home-page { padding: 0 16px !important; gap: 20px !important; }
          .lc-wordmark { font-size: 36px !important; }
          .lc-textarea { min-height: 100px !important; }
          .lc-submit-btn { width: 100% !important; }
          .lc-tile-grid { grid-template-columns: repeat(2, 1fr) !important; }
          .lc-btn-row { flex-direction: column; align-items: stretch; gap: 8px; }
        }
      `}</style>

      <div style={S.bg}>
        <div className="lc-home-page" style={S.page}>
          {/* Hero */}
          <header style={S.hero}>
            <h1 className="lc-wordmark" style={S.wordmark}>
              <span style={{ color: C.navy }}>legal</span>
              <span style={{ color: C.blue }}>clear</span>
            </h1>
            <p style={S.subhead}>Florida legal help, explained in plain English</p>
          </header>

          {/* Language toggle */}
          <div style={S.langContainer}>
            <div style={S.langPill}>
              <button style={S.langBtn(language === "en")} onClick={() => setLanguage("en")}>
                EN
              </button>
              <button style={S.langBtn(language === "es")} onClick={() => setLanguage("es")}>
                ES
              </button>
            </div>
          </div>

          {/* Intake textarea */}
          <textarea
            className="lc-textarea"
            style={S.textarea}
            value={situation}
            onChange={(e) => {
              setSituation(e.target.value);
              setClarify(null);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            onFocus={(e) => {
              e.currentTarget.style.border = `1px solid ${C.blue}`;
              e.currentTarget.style.boxShadow = "0 4px 24px rgba(67,97,238,0.18)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.border = "1px solid #E0E7FF";
              e.currentTarget.style.boxShadow = "0 4px 24px rgba(67,97,238,0.08)";
            }}
            placeholder={
              language === "es"
                ? "Describa su situación en lenguaje sencillo…"
                : "Describe your situation in plain English…"
            }
            disabled={loading}
          />

          {/* Submit */}
          <div className="lc-btn-row" style={S.btnRow}>
            <span style={S.status}>{loading ? "Analyzing…" : ""}</span>
            <button
              className="lc-submit-btn"
              style={{
                ...(isEmpty ? S.submitBtnDisabled : S.submitBtn),
                ...(hoverBtn && !isEmpty
                  ? { boxShadow: "0 6px 20px rgba(67,97,238,0.5)", filter: "brightness(1.05)" }
                  : {}),
              }}
              onMouseEnter={() => setHoverBtn(true)}
              onMouseLeave={() => setHoverBtn(false)}
              onClick={handleSubmit}
              disabled={isEmpty || loading}
            >
              {loading ? "…" : "Get Explanation"}
            </button>
          </div>

          {/* Error */}
          {error && <p style={S.error}>{error}</p>}

          {/* Clarifying question */}
          {clarify && (
            <div style={S.clarifyBox}>
              <p style={S.clarifyTitle}>Tell us a little more</p>
              <p style={S.clarifyText}>{clarify}</p>
            </div>
          )}

          {/* Module tiles grid */}
          <section style={S.navSection}>
            <p style={S.navLabel}>Or jump to a topic</p>
            <div className="lc-tile-grid" style={S.tileGrid}>
              {MODULE_TILES.map((t) => (
                <HubTile
                  key={t.to}
                  title={t.title}
                  subtitle={t.subtitle}
                  to={t.to}
                  icon={t.icon}
                />
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
