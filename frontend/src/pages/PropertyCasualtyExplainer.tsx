/**
 * Module 5 — Property & Casualty Explainer page.
 *
 * Mobile-first layout with optional document upload zone.
 *   - Sub-type badge after classification
 *   - watch_out_for → amber warning cards
 *   - relevant_florida_law → blue info card
 *   - useful_documentation → checklist
 */

import { useState, useRef, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";

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

interface ExplainResponse {
  sub_type_identified: string;
  what_this_is: string;
  what_usually_happens: string;
  typical_timeline: string;
  relevant_florida_law: string;
  useful_documentation: string[];
  watch_out_for: WarningItem[] | string[];
  typical_outcomes: string[];
  clarifying_questions: string[] | null;
  disclaimer: string;
  risk_analysis?: RiskAnalysis;
}

// ---------------------------------------------------------------------------
// SSE reader
// ---------------------------------------------------------------------------

async function* readSSE(r: ReadableStreamDefaultReader<Uint8Array>) {
  const d = new TextDecoder(); let b = "";
  while (true) {
    const { done, value } = await r.read();
    if (done) break;
    b += d.decode(value, { stream: true });
    const ls = b.split("\n"); b = ls.pop() ?? "";
    for (const l of ls) if (l.startsWith("data: ")) yield l.slice(6);
  }
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  page: { maxWidth: "var(--max-page)", margin: "0 auto", padding: "var(--space-2)" } as React.CSSProperties,
  header: { padding: "var(--space-2) 0" } as React.CSSProperties,
  back: { color: "var(--muted)", fontSize: 12, textDecoration: "none" } as React.CSSProperties,
  h1: { fontFamily: "var(--font-serif)", fontSize: 24, fontWeight: 500, margin: "8px 0 4px" } as React.CSSProperties,
  sub: { color: "var(--muted)", fontSize: 14, margin: 0 } as React.CSSProperties,
  badge: (t: string): React.CSSProperties => {
    const colors: Record<string, string> = { insurance_bad_faith: "#E8EAF6", premises_liability: "#E8F5E9", unknown: "#F5F5F5" };
    const borders: Record<string, string> = { insurance_bad_faith: "#5C6BC0", premises_liability: "#66BB6A", unknown: "#BDBDBD" };
    return { display: "inline-block", padding: "4px 14px", borderRadius: "var(--radius)", fontSize: 13, fontWeight: 500,
      background: colors[t] || "#F5F5F5", border: `1px solid ${borders[t] || "#BDBDBD"}`, marginBottom: 12 };
  },
  upload: (drag: boolean): React.CSSProperties => ({
    border: `2px dashed ${drag ? "var(--accent)" : "var(--border-strong)"}`, borderRadius: "var(--radius)",
    padding: "var(--space-3) var(--space-2)", textAlign: "center", cursor: "pointer",
    background: drag ? "#EEF2FF" : "#FAFAFA", marginBottom: "var(--space-2)", fontSize: 13, color: "var(--muted)",
  }),
  panel: { background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)",
    padding: "var(--space-2)", minHeight: 80 } as React.CSSProperties,
  sTitle: { fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "20px 0 10px" } as React.CSSProperties,
  body: { fontSize: 15, lineHeight: 1.7, margin: "0 0 12px" } as React.CSSProperties,
  amber: { background: "#FFF8E1", border: "1px solid #FFC107", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  blue: { background: "#E3F2FD", border: "1px solid #42A5F5", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 12, fontSize: 14, lineHeight: 1.6 } as React.CSSProperties,
  green: { background: "#E8F5E9", border: "1px solid #4CAF50", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  checkItem: { display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)",
    fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  checkBox: { width: 18, height: 18, border: "2px solid var(--border-strong)", borderRadius: 3, flexShrink: 0,
    marginTop: 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: "var(--muted)" } as React.CSSProperties,
  btn: { display: "block", width: "100%", padding: "12px 0", background: "var(--accent)", color: "#fff",
    border: "none", borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "pointer",
    marginBottom: "var(--space-2)" } as React.CSSProperties,
  disc: { marginTop: "var(--space-3)", padding: "var(--space-2)", background: "#f5f5f5",
    borderLeft: "3px solid var(--muted)", fontSize: 12, lineHeight: 1.6, color: "var(--muted)" } as React.CSSProperties,
  pulse: { display: "inline-block", width: 8, height: 8, borderRadius: "50%",
    background: "var(--accent)", animation: "pulse 1s infinite", marginLeft: 4 } as React.CSSProperties,
  clarify: { background: "#FFF8E1", border: "1px solid #FFC107", borderRadius: "var(--radius)",
    padding: "12px 14px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
};

function SeverityBadge({ severity }: { severity: string }) {
  const n = (severity || "").toLowerCase();
  const p = n === "high" ? { bg: "#C62828", fg: "#fff" } : n === "medium" ? { bg: "#F57F17", fg: "#000" } : { bg: "#6B6B66", fg: "#fff" };
  return <span style={{ background: p.bg, color: p.fg, padding: "2px 8px", borderRadius: "var(--radius)", fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", display: "inline-block", flexShrink: 0 }}>{n}</span>;
}

function RiskScoreCard({ risk }: { risk: RiskAnalysis }) {
  const c = risk.risk_level === "CRITICAL" ? "#B71C1C" : risk.risk_level === "HIGH" ? "#C62828" : risk.risk_level === "MEDIUM" ? "#F57F17" : "#2E7D32";
  return <div style={{ background: "#fff", border: `2px solid ${c}`, borderRadius: "var(--radius)", padding: 16, marginBottom: 16 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
      <span style={{ background: c, color: "#fff", padding: "4px 14px", borderRadius: "var(--radius)", fontSize: 14, fontWeight: 700, letterSpacing: "0.05em" }}>{risk.risk_level} RISK</span>
      <span style={{ fontSize: 13, color: "var(--muted)" }}>Score: {risk.risk_score} · {risk.high_count}H / {risk.medium_count}M / {risk.low_count}L</span>
    </div>
    <p style={{ fontSize: 14, lineHeight: 1.6, margin: "0 0 8px" }}>{risk.risk_summary}</p>
    {risk.top_concerns.length > 0 && <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.5 }}>{risk.top_concerns.map((x, i) => <li key={i}>{x}</li>)}</ul>}
  </div>;
}

function fmtSize(b: number) { return b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`; }
function subLabel(t: string) { return t === "insurance_bad_faith" ? "Insurance Bad Faith" : t === "premises_liability" ? "Premises Liability" : "Property & Casualty"; }

// ---------------------------------------------------------------------------

export default function PropertyCasualtyExplainer() {
  const [sp] = useSearchParams();
  const subType = sp.get("sub_type") || "unknown";
  const language = (sp.get("language") as "en"|"es") || "en";
  const entities: Record<string, string> = {};
  sp.forEach((v, k) => { if (!["sub_type", "language"].includes(k)) entities[k] = v; });

  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [resp, setResp] = useState<Partial<ExplainResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [raw, setRaw] = useState("");
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const inp = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }, []);

  const analyze = useCallback(async () => {
    setStreaming(true); setError(null); setRaw(""); setResp({});
    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
    const fd = new FormData();
    fd.append("sub_type", subType);
    fd.append("entities_json", JSON.stringify(entities));
    fd.append("language", language);
    if (file) fd.append("file", file);

    try {
      const res = await fetch(`${base}/api/property-casualty/explain`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      let full = "";
      for await (const c of readSSE(reader)) {
        try { const solo = JSON.parse(c); if (solo.type === "risk_analysis") { setResp(p => ({ ...p, risk_analysis: solo })); continue; } } catch {}
        full += c; setRaw(full); try { setResp(JSON.parse(full)); } catch {}
      }
      try { setResp(p => ({ ...JSON.parse(full), risk_analysis: p.risk_analysis })); } catch { if (!full.trim()) setError("Could not parse explanation."); }
    } catch (e: any) { setError(e.message); }
    finally { setStreaming(false); }
  }, [subType, entities, language, file]);

  const toggleCheck = (i: number) => setChecked(p => { const n = new Set(p); n.has(i) ? n.delete(i) : n.add(i); return n; });

  return (
    <div style={S.page}>
      <header style={S.header}>
        <Link to="/" style={S.back}>← Back to LegalClear</Link>
        <h1 style={S.h1}>Property & Casualty</h1>
        <p style={S.sub}>Florida insurance and liability situations explained</p>
      </header>

      {/* Sub-type badge */}
      <div style={S.badge(subType)}>{subLabel(subType)}</div>

      {/* Optional upload */}
      {!file && !resp.what_this_is && (
        <div style={S.upload(drag)} onDrop={onDrop} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onClick={() => inp.current?.click()}>
          📎 Attach a supporting document (optional) — PDF or image
          <input ref={inp} type="file" accept=".pdf,.jpg,.jpeg,.png,.gif,.webp" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
        </div>
      )}
      {file && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)", marginBottom: "var(--space-2)" }}>
          📎 <span style={{ flex: 1, fontSize: 14, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>{fmtSize(file.size)}</span>
          <button onClick={() => setFile(null)} style={{ background: "none", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: 18 }}>×</button>
        </div>
      )}

      {/* Analyze button */}
      {!streaming && !resp.what_this_is && <button style={S.btn} onClick={analyze}>Get Explanation</button>}

      {/* Results */}
      <div style={S.panel}>
        {error && <p style={{ color: "var(--danger)", fontSize: 14 }}>{error}</p>}
        {streaming && !resp.what_this_is && <p style={{ color: "var(--muted)", fontSize: 14, fontStyle: "italic" }}>Generating explanation<span style={S.pulse} /></p>}
        {streaming && raw && !resp.what_this_is && <p style={{ fontSize: 13, color: "var(--muted)" }}>{raw.slice(0, 200)}…</p>}

        {resp.what_this_is && (
          <>
            <h2 style={S.sTitle}>What This Is</h2>
            <p style={S.body}>{resp.what_this_is}</p>

            <h2 style={S.sTitle}>What Usually Happens</h2>
            <p style={S.body}>{resp.what_usually_happens}</p>

            <h2 style={S.sTitle}>Typical Timeline</h2>
            <p style={S.body}>{resp.typical_timeline}</p>

            {resp.relevant_florida_law && (
              <>
                <h2 style={S.sTitle}>Relevant Florida Law</h2>
                <div style={S.blue}>📜 {resp.relevant_florida_law}</div>
              </>
            )}

            {resp.useful_documentation?.length > 0 && (
              <>
                <h2 style={S.sTitle}>Useful Documentation</h2>
                {resp.useful_documentation.map((d, i) => (
                  <div key={i} style={S.checkItem} onClick={() => toggleCheck(i)}>
                    <div style={S.checkBox}>{checked.has(i) ? "✓" : ""}</div>
                    <span style={{ textDecoration: checked.has(i) ? "line-through" : "none", color: checked.has(i) ? "var(--muted)" : "var(--fg)" }}>{d}</span>
                  </div>
                ))}
              </>
            )}

            {/* ── Risk Analysis Card ── */}
            {resp.risk_analysis && <RiskScoreCard risk={resp.risk_analysis} />}

            {resp.watch_out_for?.length > 0 && (
              <>
                <h2 style={S.sTitle}>Watch Out For</h2>
                {resp.watch_out_for.map((w, i) => {
                  const desc = typeof w === "string" ? w : w.description;
                  const sev = typeof w === "string" ? "medium" : w.severity;
                  const ask = typeof w === "string" ? "" : w.ask_attorney;
                  return <div key={i} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 14, marginBottom: 10, background: sev === "high" ? "#FFEBEE" : sev === "medium" ? "#FFF8E1" : "#FAFAFA" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}><SeverityBadge severity={sev} /></div>
                    <p style={{ margin: "0 0 8px", fontSize: 14, lineHeight: 1.6 }}>⚠ {desc}</p>
                    {ask && <div style={{ border: "1px solid var(--border)", padding: 10, background: "var(--bg-elevated, #fafafa)", borderRadius: "var(--radius)" }}><p style={{ margin: "0 0 4px", fontSize: 11, color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>Ask Your Attorney About</p><p style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>{ask}</p></div>}
                  </div>;
                })}
              </>
            )}

            {resp.typical_outcomes?.length > 0 && (
              <>
                <h2 style={S.sTitle}>Typical Outcomes</h2>
                {resp.typical_outcomes.map((o, i) => <div key={i} style={S.green}>✓ {o}</div>)}
              </>
            )}

            {resp.clarifying_questions?.length > 0 && (
              <>
                <h2 style={S.sTitle}>Clarifying Questions</h2>
                {resp.clarifying_questions.map((q, i) => <div key={i} style={S.clarify}>? {q}</div>)}
              </>
            )}
          </>
        )}
      </div>

      <div style={S.disc}>{resp.disclaimer || "LegalClear provides legal information, not legal advice."}</div>

      <ChatButton module="property_casualty" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer module="property_casualty" onClose={() => setChatOpen(false)} />
      )}
    </div>
  );
}
