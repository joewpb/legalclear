/**
 * Module 4 — Discovery Motion Analyzer page.
 *
 * Mobile-first upload zone (PDF/image) + streaming analysis.
 *   - discrepancies → red highlight cards
 *   - what_missing → amber warning cards
 *   - what_present → green confirmation cards
 *   - likely_resistance → orange caution cards
 */

import { useState, useRef, useCallback } from "react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnalysisResponse {
  summary: string;
  what_requested: string[];
  what_present: string[];
  what_missing: string[];
  discrepancies: string[];
  likely_production: string[];
  likely_resistance: string[];
  disclaimer: string;
}

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
      if (line.startsWith("data: ")) yield line.slice(6);
    }
  }
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  page: { maxWidth: "var(--max-page, 1140px)", margin: "0 auto", padding: "var(--space-2, 16px)" } as React.CSSProperties,
  header: { padding: "var(--space-2, 16px) 0" } as React.CSSProperties,
  back: { color: "var(--muted)", fontSize: 12, textDecoration: "none" } as React.CSSProperties,
  h1: { fontFamily: "var(--font-serif)", fontSize: 24, fontWeight: 500, margin: "8px 0 4px" } as React.CSSProperties,
  sub: { color: "var(--muted)", fontSize: 14, margin: 0 } as React.CSSProperties,
  upload: (drag: boolean): React.CSSProperties => ({
    border: `2px dashed ${drag ? "var(--accent)" : "var(--border-strong)"}`,
    borderRadius: "var(--radius)", padding: "var(--space-4) var(--space-2)",
    textAlign: "center", cursor: "pointer", background: drag ? "#EEF2FF" : "#FAFAFA",
    transition: "all 0.2s", marginBottom: "var(--space-2)",
  }),
  preview: { display: "flex", alignItems: "center", gap: 12, padding: "10px 14px",
    background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)",
    marginBottom: "var(--space-2)" } as React.CSSProperties,
  panel: { background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)",
    padding: "var(--space-2)", minHeight: 80 } as React.CSSProperties,
  sTitle: { fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "20px 0 10px" } as React.CSSProperties,
  body: { fontSize: 15, lineHeight: 1.7, margin: "0 0 12px" } as React.CSSProperties,
  red: { background: "#FFEBEE", border: "1px solid #EF5350", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  amber: { background: "#FFF8E1", border: "1px solid #FFC107", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  green: { background: "#E8F5E9", border: "1px solid #4CAF50", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  orange: { background: "#FFF3E0", border: "1px solid #FF9800", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  btn: { display: "block", width: "100%", padding: "12px 0", background: "var(--accent)", color: "#fff",
    border: "none", borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "pointer",
    marginBottom: "var(--space-2)" } as React.CSSProperties,
  disc: { marginTop: "var(--space-3)", padding: "var(--space-2)", background: "#f5f5f5",
    borderLeft: "3px solid var(--muted)", fontSize: 12, lineHeight: 1.6, color: "var(--muted)" } as React.CSSProperties,
  pulse: { display: "inline-block", width: 8, height: 8, borderRadius: "50%",
    background: "var(--accent)", animation: "pulse 1s infinite", marginLeft: 4 } as React.CSSProperties,
};

function fmtSize(b: number) { return b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB`; }

// ---------------------------------------------------------------------------

export default function DiscoveryMotionAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [resp, setResp] = useState<Partial<AnalysisResponse>>({});
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [raw, setRaw] = useState("");
  const inp = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }, []);
  const analyze = useCallback(async () => {
    if (!file) return;
    setStreaming(true); setError(null); setRaw(""); setResp({});
    const base = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
    const fd = new FormData(); fd.append("file", file); fd.append("language", "en");
    try {
      const res = await fetch(`${base}/api/discovery/analyze`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      let full = "";
      for await (const c of readSSE(reader)) { full += c; setRaw(full); try { setResp(JSON.parse(full)); } catch { /* */ } }
      try { setResp(JSON.parse(full)); } catch { setError("Could not parse analysis."); }
    } catch (e: any) { setError(e.message); }
    finally { setStreaming(false); }
  }, [file]);

  return (
    <div style={S.page}>
      <header style={S.header}>
        <Link to="/" style={S.back}>← Back to LegalClear</Link>
        <h1 style={S.h1}>Motion for Discovery Analyzer</h1>
        <p style={S.sub}>Florida Rule of Criminal Procedure 3.220</p>
      </header>

      {!file ? (
        <div style={S.upload(drag)} onDrop={onDrop} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onClick={() => inp.current?.click()}>
          <div style={{ fontSize: 32, marginBottom: 8, color: "var(--muted)" }}>📋</div>
          <p style={{ fontSize: 14, color: "var(--muted)", margin: 0 }}>Drop a motion for discovery here or tap to upload</p>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0" }}>PDF, JPG, PNG — up to 15 MB</p>
          <input ref={inp} type="file" accept=".pdf,.jpg,.jpeg,.png,.gif,.webp" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
        </div>
      ) : (
        <>
          <div style={S.preview}>
            <span style={{ fontSize: 20 }}>📎</span>
            <span style={{ flex: 1, fontSize: 14, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>{fmtSize(file.size)}</span>
            <button onClick={() => { setFile(null); setResp({}); setRaw(""); setError(null); }} style={{ background: "none", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: 18 }}>×</button>
          </div>
          {!streaming && !resp.summary && <button style={S.btn} onClick={analyze}>Analyze Motion</button>}
        </>
      )}

      <div style={S.panel}>
        {error && <p style={{ color: "var(--danger)", fontSize: 14 }}>{error}</p>}
        {streaming && !resp.summary && <p style={{ color: "var(--muted)", fontSize: 14, fontStyle: "italic" }}>Analyzing motion<span style={S.pulse} /></p>}
        {streaming && raw && !resp.summary && <p style={{ fontSize: 13, color: "var(--muted)" }}>{raw.slice(0, 200)}…</p>}

        {resp.summary && (
          <>
            <h2 style={S.sTitle}>Summary</h2>
            <p style={S.body}>{resp.summary}</p>

            {resp.what_requested?.length > 0 && <><h2 style={S.sTitle}>What Is Being Requested</h2><ul style={{ padding: "0 0 0 18px", margin: 0 }}>{resp.what_requested.map((r, i) => <li key={i} style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 4 }}>{r}</li>)}</ul></>}

            {resp.what_present?.length > 0 && <><h2 style={S.sTitle}>Present & Properly Stated</h2>{resp.what_present.map((p, i) => <div key={i} style={S.green}>✓ {p}</div>)}</>}

            {resp.what_missing?.length > 0 && <><h2 style={S.sTitle}>Missing vs. Rule 3.220</h2>{resp.what_missing.map((m, i) => <div key={i} style={S.amber}>⚡ {m}</div>)}</>}

            {resp.discrepancies?.length > 0 && <><h2 style={S.sTitle}>Discrepancies & Gaps</h2>{resp.discrepancies.map((d, i) => <div key={i} style={S.red}>⚠ {d}</div>)}</>}

            {resp.likely_production?.length > 0 && <><h2 style={S.sTitle}>Likely to Be Produced</h2>{resp.likely_production.map((p, i) => <div key={i} style={S.green}>📄 {p}</div>)}</>}

            {resp.likely_resistance?.length > 0 && <><h2 style={S.sTitle}>Likely to Be Resisted</h2>{resp.likely_resistance.map((r, i) => <div key={i} style={S.orange}>🛡 {r}</div>)}</>}
          </>
        )}
      </div>

      <div style={S.disc}>{resp.disclaimer || "LegalClear provides legal information, not legal advice. Nothing here creates an attorney-client relationship."}</div>
    </div>
  );
}
