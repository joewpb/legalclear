/**
 * Module 5 — Property & Casualty Explainer page.
 *
 * Mobile-first layout. One input, AI routes.
 *   - 48px minimum touch targets
 *   - NO client-side date arithmetic — deadlines rendered verbatim from backend
 *   - NO directive framing in static copy (third-person/informational only)
 *   - Disclaimer visible at all times
 *
 * Sub-types: first_party_property, insurance_bad_faith, premises_liability
 */

import { useState, useRef, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";
import { readSSE } from "../lib/sse";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WarningItem {
  severity: "high" | "medium" | "low";
  description: string;
  ask_attorney: string;
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

interface DeadlineItem {
  label: string;
  due_date: string;
  governing_rule: string;
  severity: string;
  consequence: string;
  is_past: boolean;
  deadline_type: "SOL" | "insurer_deadline" | "pre_suit_gate" | "court_filing";
  computation_trace: { step: number; action: string; date: string | null; rule: string }[];
}

interface ExplainResponse {
  sub_type_identified: string;
  what_this_is: string;
  what_usually_happens?: string;
  typical_timeline: string;
  relevant_florida_law: string;
  useful_documentation: string[];
  watch_out_for: WarningItem[] | string[];
  typical_outcomes?: string[];
  key_deadlines?: DeadlineItem[];          // first-party only — backend-computed
  resolution_options?: string[];           // first-party only
  clarifying_questions: string[] | null;
  disclaimer: string;
  risk_analysis?: RiskAnalysis;
}

// ---------------------------------------------------------------------------
// Styles — 48px touch targets throughout
// ---------------------------------------------------------------------------

const TOUCH_MIN = 48; // px

const S = {
  page: { maxWidth: "var(--max-page)", margin: "0 auto", padding: "var(--space-2)" } as React.CSSProperties,
  header: { padding: "var(--space-2) 0" } as React.CSSProperties,
  back: { color: "var(--muted)", fontSize: 12, textDecoration: "none" } as React.CSSProperties,
  h1: { fontFamily: "var(--font-serif)", fontSize: 24, fontWeight: 500, margin: "8px 0 4px" } as React.CSSProperties,
  sub: { color: "var(--muted)", fontSize: 14, margin: 0 } as React.CSSProperties,
  badge: (t: string): React.CSSProperties => {
    const colors: Record<string, string> = {
      first_party_property: "#E8EAF6", insurance_bad_faith: "#FFF3E0",
      premises_liability: "#E8F5E9", unknown: "#F5F5F5"
    };
    const borders: Record<string, string> = {
      first_party_property: "#5C6BC0", insurance_bad_faith: "#FF9800",
      premises_liability: "#66BB6A", unknown: "#BDBDBD"
    };
    return { display: "inline-block", padding: "6px 16px", borderRadius: "var(--radius)",
      fontSize: 13, fontWeight: 500,
      background: colors[t] || "#F5F5F5", border: `1px solid ${borders[t] || "#BDBDBD"}`,
      marginBottom: 12, minHeight: 32 };
  },
  upload: (drag: boolean): React.CSSProperties => ({
    border: `2px dashed ${drag ? "var(--accent)" : "var(--border-strong)"}`,
    borderRadius: "var(--radius)", padding: "var(--space-3) var(--space-2)",
    textAlign: "center", cursor: "pointer", background: drag ? "#EEF2FF" : "#FAFAFA",
    marginBottom: "var(--space-2)", fontSize: 13, color: "var(--muted)",
    minHeight: TOUCH_MIN, display: "flex", alignItems: "center", justifyContent: "center",
  }),
  panel: { background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)",
    padding: "var(--space-2)", minHeight: 80 } as React.CSSProperties,
  sTitle: { fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500,
    margin: "20px 0 10px" } as React.CSSProperties,
  body: { fontSize: 15, lineHeight: 1.7, margin: "0 0 12px" } as React.CSSProperties,
  blue: { background: "#E3F2FD", border: "1px solid #42A5F5", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 12, fontSize: 14, lineHeight: 1.6 } as React.CSSProperties,
  green: { background: "#E8F5E9", border: "1px solid #4CAF50", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  checkItem: { display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0",
    borderBottom: "1px solid var(--border)", fontSize: 14, lineHeight: 1.5,
    minHeight: TOUCH_MIN } as React.CSSProperties,
  checkBox: { width: TOUCH_MIN, height: TOUCH_MIN, border: "2px solid var(--border-strong)",
    borderRadius: 3, flexShrink: 0, display: "flex", alignItems: "center",
    justifyContent: "center", fontSize: 16, color: "var(--muted)",
    cursor: "pointer", background: "#fff" } as React.CSSProperties,
  btn: { display: "block", width: "100%", minHeight: TOUCH_MIN, padding: "0 0",
    background: "var(--accent)", color: "#fff", border: "none",
    borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "pointer",
    marginBottom: "var(--space-2)" } as React.CSSProperties,
  disc: { marginTop: "var(--space-3)", padding: "var(--space-2)", background: "#f5f5f5",
    borderLeft: "3px solid var(--muted)", fontSize: 12, lineHeight: 1.6,
    color: "var(--muted)" } as React.CSSProperties,
  pulse: { display: "inline-block", width: 8, height: 8, borderRadius: "50%",
    background: "var(--accent)", animation: "pulse 1s infinite", marginLeft: 4 } as React.CSSProperties,
  clarify: { background: "#FFF8E1", border: "1px solid #FFC107", borderRadius: "var(--radius)",
    padding: "12px 14px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  // ── Deadline cards (first-party only) ──
  deadlineCard: (isPast: boolean, sev: string): React.CSSProperties => ({
    border: `1px solid ${sev === "fatal" ? "#C62828" : sev === "high" ? "#F57F17" : "var(--border)"}`,
    borderRadius: "var(--radius)", padding: 14, marginBottom: 10,
    background: isPast ? "#FFEBEE" : sev === "fatal" ? "#FFF5F5" : sev === "high" ? "#FFFDE7" : "#FAFAFA",
    opacity: isPast ? 0.75 : 1,
  }),
  deadlineDate: { fontSize: 20, fontWeight: 600, fontFamily: "var(--mono-font, monospace)",
    letterSpacing: "0.02em", margin: "4px 0" } as React.CSSProperties,
  deadlineRule: { fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono-font, monospace)",
    letterSpacing: "0.04em", textTransform: "uppercase" as const },
  deadlineLabel: { fontSize: 14, fontWeight: 500, margin: "0 0 4px" } as React.CSSProperties,
  deadlineConsequence: { fontSize: 13, lineHeight: 1.5, margin: "6px 0 0",
    color: "var(--fg-secondary, #555)" } as React.CSSProperties,
  pastBadge: { display: "inline-block", background: "#C62828", color: "#fff",
    padding: "2px 8px", borderRadius: "var(--radius)", fontSize: 10, fontWeight: 700,
    letterSpacing: "0.08em", textTransform: "uppercase" as const, marginLeft: 8 },
  // ── Resolution options ──
  resOption: { display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 0",
    borderBottom: "1px solid var(--border)", fontSize: 14, lineHeight: 1.5,
    minHeight: TOUCH_MIN } as React.CSSProperties,
  resBullet: { width: TOUCH_MIN, height: TOUCH_MIN, flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 18 } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SeverityBadge({ severity }: { severity: string }) {
  const n = (severity || "").toLowerCase();
  const p = n === "high" || n === "fatal" ? { bg: "#C62828", fg: "#fff" }
    : n === "medium" ? { bg: "#F57F17", fg: "#000" }
    : { bg: "#6B6B66", fg: "#fff" };
  return <span style={{ background: p.bg, color: p.fg, padding: "2px 8px",
    borderRadius: "var(--radius)", fontSize: 11, fontWeight: 600,
    letterSpacing: "0.08em", textTransform: "uppercase", display: "inline-block",
    flexShrink: 0 }}>{n}</span>;
}

function RiskScoreCard({ risk }: { risk: RiskAnalysis }) {
  const c = risk.risk_level === "CRITICAL" ? "#B71C1C"
    : risk.risk_level === "HIGH" ? "#C62828"
    : risk.risk_level === "MEDIUM" ? "#F57F17" : "#2E7D32";
  return <div style={{ background: "#fff", border: `2px solid ${c}`,
    borderRadius: "var(--radius)", padding: 16, marginBottom: 16 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
      <span style={{ background: c, color: "#fff", padding: "4px 14px",
        borderRadius: "var(--radius)", fontSize: 14, fontWeight: 700,
        letterSpacing: "0.05em" }}>{risk.risk_level} RISK</span>
      <span style={{ fontSize: 13, color: "var(--muted)" }}>
        Score: {risk.risk_score} · {risk.high_count}H / {risk.medium_count}M / {risk.low_count}L</span>
    </div>
    <p style={{ fontSize: 14, lineHeight: 1.6, margin: "0 0 8px" }}>{risk.risk_summary}</p>
    {risk.top_concerns.length > 0 && <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.5 }}>
      {risk.top_concerns.map((x, i) => <li key={i}>{x}</li>)}</ul>}
  </div>;
}

/** Renders backend-computed deadlines verbatim — ZERO client-side date math. */
function DeadlineCard({ dl }: { dl: DeadlineItem }) {
  const typeLabel = dl.deadline_type === "SOL"
    ? "Statutory deadline"
    : dl.deadline_type === "insurer_deadline"
    ? "Insurer deadline"
    : dl.deadline_type === "pre_suit_gate"
    ? "Pre-suit requirement"
    : "Court deadline";
  return (
    <div style={S.deadlineCard(dl.is_past, dl.severity)}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div style={S.deadlineLabel}>
          {dl.label}
          {dl.is_past && <span style={S.pastBadge}>passed</span>}
        </div>
        <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 4 }}>
          {typeLabel}
        </div>
        <SeverityBadge severity={dl.severity} />
      </div>
      <div style={S.deadlineDate}>
        {dl.due_date}
      </div>
      <div style={S.deadlineRule}>{dl.governing_rule}</div>
      <div style={S.deadlineConsequence}>{dl.consequence}</div>
    </div>
  );
}

/** Renders resolution options — informational, no directive framing. */
function ResolutionOptions({ options }: { options: string[] }) {
  if (!options || options.length === 0) return null;
  return (
    <>
      <h2 style={S.sTitle}>Resolution Options</h2>
      {options.map((o, i) => (
        <div key={i} style={S.resOption}>
          <div style={S.resBullet}>→</div>
          <span>{o}</span>
        </div>
      ))}
    </>
  );
}

function fmtSize(b: number) { return b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`; }

function subLabel(t: string) {
  const labels: Record<string, string> = {
    first_party_property: "First-Party Property Claim",
    insurance_bad_faith: "Insurance Bad Faith",
    premises_liability: "Premises Liability",
  };
  return labels[t] || "Property & Casualty";
}

// ---------------------------------------------------------------------------

export default function PropertyCasualtyExplainer() {
  const [sp] = useSearchParams();
  const subType = sp.get("sub_type") || "unknown";
  const language = (sp.get("language") as "en"|"es") || "en";
  const entities: Record<string, string> = {};
  sp.forEach((v, k) => { if (!["sub_type", "language"].includes(k)) entities[k] = v; });

  const [file, setFile] = useState<File | null>(null);
  // date_of_loss — required trigger input for the deterministic deadline engine
  // (first-party only). Without it the backend cannot compute key_deadlines and
  // the "Key Deadlines" section never renders. Seeded from ?date_of_loss= if present.
  const [lossDate, setLossDate] = useState<string>(entities.date_of_loss || "");
  const [drag, setDrag] = useState(false);
  const [resp, setResp] = useState<Partial<ExplainResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [raw, setRaw] = useState("");
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const inp = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files?.[0]; if (f) setFile(f);
  }, []);

  const analyze = useCallback(async () => {
    setStreaming(true); setError(null); setRaw(""); setResp({});
    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
    // Merge lossDate into entities so the backend can parse date_of_loss and
    // run the deterministic deadline computation (first-party property only).
    const effEntities = { ...entities, ...(lossDate ? { date_of_loss: lossDate } : {}) };
    const fd = new FormData();
    fd.append("sub_type", subType);
    fd.append("entities_json", JSON.stringify(effEntities));
    fd.append("language", language);
    if (file) fd.append("file", file);

    try {
      const res = await fetch(`${base}/api/property-casualty/explain`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      let full = "";
      for await (const { event, data: c } of readSSE(reader)) {
        if (event === "disclaimer") {
          try {
            const parsed = JSON.parse(c);
            setResp(p => ({ ...p, disclaimer: parsed.disclaimer ?? c }));
          } catch {
            setResp(p => ({ ...p, disclaimer: c }));
          }
          continue;
        }
        if (event !== "message") {
          console.debug(`[SSE] ignoring unknown event type: ${event}`);
          continue;
        }
        try { const solo = JSON.parse(c);
          if (solo.type === "risk_analysis") { setResp(p => ({ ...p, risk_analysis: solo })); continue; }
        } catch {}
        full += c; setRaw(full);
        try { setResp(JSON.parse(full)); } catch {}
      }
      try {
        // Preserve risk_analysis and disclaimer from streaming updates
        setResp(p => {
          const parsed = JSON.parse(full);
          return { ...parsed, risk_analysis: p.risk_analysis, disclaimer: p.disclaimer ?? parsed.disclaimer };
        });
      } catch { if (!full.trim()) setError("Could not parse explanation."); }
    } catch (e: any) { setError(e.message); }
    finally { setStreaming(false); }
  }, [subType, entities, lossDate, language, file]);

  const toggleCheck = (i: number) => setChecked(p => {
    const n = new Set(p); n.has(i) ? n.delete(i) : n.add(i); return n;
  });

  const isFirstParty = subType === "first_party_property" || resp.sub_type_identified === "first_party_property";

  return (
    <div style={S.page}>
      <header style={S.header}>
        <Link to="/" style={S.back}>← Back to LegalClear</Link>
        <h1 style={S.h1}>Property & Casualty</h1>
        <p style={S.sub}>Florida property insurance claims explained</p>
      </header>

      {/* Sub-type badge */}
      <div style={S.badge(subType)}>{subLabel(subType)}</div>

      {/* Optional upload */}
      {!file && !resp.what_this_is && (
        <div style={S.upload(drag)}
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onClick={() => inp.current?.click()}>
          📎 Attach a supporting document (optional) — PDF or image
          <input ref={inp} type="file" accept=".pdf,.jpg,.jpeg,.png,.gif,.webp"
            style={{ display: "none" }}
            onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
        </div>
      )}
      {file && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, minHeight: TOUCH_MIN,
          padding: "10px 14px", background: "#fff", border: "1px solid var(--border)",
          borderRadius: "var(--radius)", marginBottom: "var(--space-2)" }}>
          📎 <span style={{ flex: 1, fontSize: 14, fontWeight: 500, overflow: "hidden",
            textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>{fmtSize(file.size)}</span>
          <button onClick={() => setFile(null)} style={{ background: "none", border: "none",
            color: "var(--danger)", cursor: "pointer", fontSize: 18,
            minWidth: TOUCH_MIN, minHeight: TOUCH_MIN, display: "flex",
            alignItems: "center", justifyContent: "center" }}>×</button>
        </div>
      )}

      {/* Date of loss — first-party only; required to compute statutory deadlines */}
      {!resp.what_this_is && (
        <div style={{ marginBottom: "var(--space-2)", display: "flex",
          flexDirection: "column", gap: 6 }}>
          <label htmlFor="pc-loss-date" style={{ fontSize: 14, fontWeight: 500 }}>
            Date of loss
          </label>
          <input id="pc-loss-date" type="date" value={lossDate}
            onChange={e => setLossDate(e.target.value)}
            style={{ padding: "10px 12px", fontSize: 16, minHeight: TOUCH_MIN,
              border: "1px solid var(--border)", borderRadius: "var(--radius)",
              background: "#fff", color: "var(--text)" }} />
          {!lossDate && (
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              Enter your date of loss to see your statutory deadlines.
            </span>
          )}
        </div>
      )}

      {/* Analyze button — 48px touch target */}
      {!streaming && !resp.what_this_is && (
        <button style={S.btn} onClick={analyze}>Get Explanation</button>
      )}

      {/* Results */}
      <div style={S.panel}>
        {error && <p style={{ color: "var(--danger)", fontSize: 14 }}>{error}</p>}
        {streaming && !resp.what_this_is && (
          <p style={{ color: "var(--muted)", fontSize: 14, fontStyle: "italic" }}>
            Generating explanation<span style={S.pulse} /></p>
        )}
        {streaming && raw && !resp.what_this_is && (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>{raw.slice(0, 200)}…</p>
        )}

        {resp.what_this_is && (
          <>
            <h2 style={S.sTitle}>What This Is</h2>
            <p style={S.body}>{resp.what_this_is}</p>

            {/* ── KEY DEADLINES — first-party only, backend-computed, rendered verbatim ── */}
            {isFirstParty && resp.key_deadlines && resp.key_deadlines.length > 0 && (
              <>
                <h2 style={S.sTitle}>Key Deadlines</h2>
                <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
                  Deadlines computed from the date of loss. The report and suit
                  clocks are statutory deadlines; the pay-or-deny and notice
                  periods are procedural. Dates are raw anniversary values —
                  a deadline falling on a weekend or holiday may have a later
                  court-filing date under Rule 2.514.
                </p>
                {resp.key_deadlines.map((dl, i) => (
                  <DeadlineCard key={i} dl={dl} />
                ))}
              </>
            )}

            {resp.what_usually_happens && (
              <>
                <h2 style={S.sTitle}>What Usually Happens</h2>
                <p style={S.body}>{resp.what_usually_happens}</p>
              </>
            )}

            <h2 style={S.sTitle}>Typical Timeline</h2>
            <p style={S.body}>{resp.typical_timeline}</p>

            {resp.relevant_florida_law && (
              <>
                <h2 style={S.sTitle}>Relevant Florida Law</h2>
                <div style={S.blue}>📜 {resp.relevant_florida_law}</div>
              </>
            )}

            {/* ── RESOLUTION OPTIONS — first-party only ── */}
            {isFirstParty && resp.resolution_options && (
              <ResolutionOptions options={resp.resolution_options} />
            )}

            {resp.useful_documentation && resp.useful_documentation.length > 0 && (
              <>
                <h2 style={S.sTitle}>Useful Documentation</h2>
                {resp.useful_documentation.map((d, i) => (
                  <div key={i} style={S.checkItem} onClick={() => toggleCheck(i)}>
                    <div style={S.checkBox}>{checked.has(i) ? "✓" : ""}</div>
                    <span style={{ textDecoration: checked.has(i) ? "line-through" : "none",
                      color: checked.has(i) ? "var(--muted)" : "var(--fg)" }}>{d}</span>
                  </div>
                ))}
              </>
            )}

            {/* ── Risk Analysis Card ── */}
            {resp.risk_analysis && <RiskScoreCard risk={resp.risk_analysis} />}

            {resp.watch_out_for && resp.watch_out_for.length > 0 && (
              <>
                <h2 style={S.sTitle}>Watch Out For</h2>
                {resp.watch_out_for.map((w, i) => {
                  const desc = typeof w === "string" ? w : w.description;
                  const sev = typeof w === "string" ? "medium" : w.severity;
                  const ask = typeof w === "string" ? "" : w.ask_attorney;
                  return <div key={i} style={{
                    border: "1px solid var(--border)", borderRadius: "var(--radius)",
                    padding: 14, marginBottom: 10,
                    background: sev === "high" ? "#FFEBEE" : sev === "medium" ? "#FFF8E1" : "#FAFAFA"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <SeverityBadge severity={sev} />
                    </div>
                    <p style={{ margin: "0 0 8px", fontSize: 14, lineHeight: 1.6 }}>⚠ {desc}</p>
                    {ask && <div style={{ border: "1px solid var(--border)", padding: 10,
                      background: "var(--bg-elevated, #fafafa)", borderRadius: "var(--radius)" }}>
                      <p style={{ margin: "0 0 4px", fontSize: 11, color: "var(--muted)",
                        letterSpacing: "0.08em", textTransform: "uppercase" }}>
                        Ask Your Attorney About</p>
                      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>{ask}</p>
                    </div>}
                  </div>;
                })}
              </>
            )}

            {resp.typical_outcomes && resp.typical_outcomes.length > 0 && (
              <>
                <h2 style={S.sTitle}>Typical Outcomes</h2>
                {resp.typical_outcomes.map((o, i) => (
                  <div key={i} style={S.green}>✓ {o}</div>
                ))}
              </>
            )}

            {resp.clarifying_questions && resp.clarifying_questions.length > 0 && (
              <>
                <h2 style={S.sTitle}>Clarifying Questions</h2>
                {resp.clarifying_questions.map((q, i) => (
                  <div key={i} style={S.clarify}>? {q}</div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      <div style={S.disc}>
        {resp.disclaimer || "LegalClear provides legal information, not legal advice."}
      </div>

      <ChatButton module="property_casualty" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer module="property_casualty" onClose={() => setChatOpen(false)} />
      )}
    </div>
  );
}
