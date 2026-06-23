/**
 * Module 6 — Wills & Trusts Explainer page.
 *
 * Mobile-first layout with sub-type selector tabs:
 *   [Will] [Trust] [Probate] [Draft a Will]
 * Situation textarea → streaming AI response via SSE.
 * Draft Will sub-type shows structured input form + generated boilerplate.
 * ChatDrawer integration for conversational follow-up.
 */

import { useState, useRef, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ChatDrawer, { ChatButton } from "../components/ChatDrawer";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WillsTrustsResponse {
  sub_type_identified: string;
  what_this_means: string;
  florida_requirements: string[];
  typical_process: string;
  probate_implications: string;
  useful_documents: string[];
  watch_out_for: string[];
  draft_content: string | null;
  disclaimer: string;
}

interface DraftInputs {
  fullName: string;
  county: string;
  maritalStatus: string;
  spouseName: string;
  children: string;
  assets: string;
  beneficiaries: string;
  executor: string;
  guardian: string;
  specialBequests: string;
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
// Constants
// ---------------------------------------------------------------------------

const SUB_TYPES = ["will", "trust", "probate", "draft_will"] as const;
type SubType = (typeof SUB_TYPES)[number];

const SUB_LABELS: Record<SubType, string> = {
  will: "Will",
  trust: "Trust",
  probate: "Probate",
  draft_will: "Draft a Will",
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  page: { maxWidth: "var(--max-page, 720px)", margin: "0 auto", padding: "var(--space-2, 16px)" } as React.CSSProperties,
  header: { padding: "var(--space-2, 16px) 0" } as React.CSSProperties,
  back: { color: "var(--muted, #6B7280)", fontSize: 12, textDecoration: "none" } as React.CSSProperties,
  h1: { fontFamily: "var(--font-serif, Georgia)", fontSize: 24, fontWeight: 500, margin: "8px 0 4px" } as React.CSSProperties,
  sub: { color: "var(--muted, #6B7280)", fontSize: 14, margin: 0 } as React.CSSProperties,

  /* Tabs */
  tabs: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap" as const,
    margin: "16px 0",
  } as React.CSSProperties,
  tab: (active: boolean): React.CSSProperties => ({
    padding: "8px 18px",
    border: active ? "2px solid #4361EE" : "2px solid #E0E7FF",
    borderRadius: 24,
    background: active ? "#4361EE" : "#fff",
    color: active ? "#fff" : "#1A1A2E",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    transition: "all 0.2s",
  }),

  /* Textarea */
  textarea: {
    width: "100%",
    minHeight: 100,
    padding: "12px 16px",
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    fontSize: 14,
    lineHeight: 1.6,
    resize: "vertical" as const,
    fontFamily: "inherit",
    boxSizing: "border-box" as const,
  } as React.CSSProperties,

  /* Button */
  submitBtn: {
    marginTop: 12,
    padding: "12px 28px",
    border: "none",
    borderRadius: 16,
    background: "linear-gradient(135deg, #4361EE, #3A0CA3)",
    color: "#fff",
    fontWeight: 600,
    fontSize: 15,
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(67,97,238,0.3)",
  } as React.CSSProperties,
  submitBtnDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
    boxShadow: "none",
  } as React.CSSProperties,

  /* Response panel */
  responsePanel: {
    marginTop: 20,
    padding: "20px 24px",
    background: "#fff",
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
  } as React.CSSProperties,
  sTitle: { fontSize: 16, fontWeight: 600, margin: "16px 0 8px", color: "#1A1A2E" } as React.CSSProperties,
  bodyText: { fontSize: 14, lineHeight: 1.7, color: "#1A1A2E", whiteSpace: "pre-wrap" as const } as React.CSSProperties,

  /* Info cards */
  blueCard: {
    padding: "10px 14px",
    background: "#EEF2FF",
    borderLeft: "4px solid #4361EE",
    borderRadius: 8,
    margin: "6px 0",
    fontSize: 14,
    lineHeight: 1.5,
  } as React.CSSProperties,
  amberCard: {
    padding: "10px 14px",
    background: "#FFFBEB",
    borderLeft: "4px solid #F59E0B",
    borderRadius: 8,
    margin: "6px 0",
    fontSize: 14,
    lineHeight: 1.5,
  } as React.CSSProperties,

  /* Draft content — clean document style */
  draftDoc: {
    marginTop: 12,
    padding: "24px 28px",
    background: "#FAFBFD",
    border: "1px solid #E0E7FF",
    borderRadius: 12,
    fontFamily: "monospace",
    fontSize: 13,
    lineHeight: 1.8,
    whiteSpace: "pre-wrap" as const,
    maxHeight: 500,
    overflowY: "auto" as const,
  } as React.CSSProperties,
  downloadBtn: {
    display: "inline-block",
    marginTop: 12,
    padding: "8px 18px",
    border: "2px solid #4361EE",
    borderRadius: 16,
    background: "#fff",
    color: "#4361EE",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
  } as React.CSSProperties,

  /* Draft form */
  draftForm: {
    marginTop: 12,
    display: "flex",
    flexDirection: "column" as const,
    gap: 12,
  } as React.CSSProperties,
  formLabel: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1A1A2E",
    marginBottom: 2,
  } as React.CSSProperties,
  formInput: {
    width: "100%",
    padding: "8px 12px",
    border: "1px solid #E0E7FF",
    borderRadius: 8,
    fontSize: 14,
    fontFamily: "inherit",
    boxSizing: "border-box" as const,
  } as React.CSSProperties,

  /* Disclaimer */
  disc: {
    marginTop: 16,
    padding: "10px 14px",
    background: "#f5f5f5",
    borderLeft: "3px solid #6B7280",
    fontSize: 11,
    lineHeight: 1.5,
    color: "#6B7280",
  } as React.CSSProperties,

  /* Loading */
  loading: {
    textAlign: "center" as const,
    padding: 20,
    color: "#6B7280",
    fontSize: 14,
    fontStyle: "italic",
  } as React.CSSProperties,

  /* Error */
  error: { color: "#DC2626", fontSize: 14, marginTop: 12 } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Draft form component
// ---------------------------------------------------------------------------

const INITIAL_DRAFT: DraftInputs = {
  fullName: "",
  county: "",
  maritalStatus: "",
  spouseName: "",
  children: "",
  assets: "",
  beneficiaries: "",
  executor: "",
  guardian: "",
  specialBequests: "",
};

function DraftForm({
  inputs,
  onChange,
  onGenerate,
  loading,
}: {
  inputs: DraftInputs;
  onChange: (f: DraftInputs) => void;
  onGenerate: () => void;
  loading: boolean;
}) {
  const update = (key: keyof DraftInputs, val: string) =>
    onChange({ ...inputs, [key]: val });

  const fields: { key: keyof DraftInputs; label: string; placeholder: string; multiline?: boolean }[] = [
    { key: "fullName", label: "1. Full legal name and FL county", placeholder: "e.g. Jane Doe, Miami-Dade County" },
    { key: "maritalStatus", label: "2. Marital status and spouse name", placeholder: "e.g. Married to John Doe, or Single" },
    { key: "children", label: "3. Children names and ages", placeholder: "e.g. Emily Doe (12), Michael Doe (8)" },
    { key: "assets", label: "4. Major assets", placeholder: "e.g. home at 123 Main St, checking account at Chase, 2020 Toyota Camry", multiline: true },
    { key: "beneficiaries", label: "5. Beneficiaries and percentages", placeholder: "e.g. John Doe (spouse) 50%, Emily Doe (daughter) 25%, Michael Doe (son) 25%" },
    { key: "executor", label: "6. Executor (personal representative) name", placeholder: "e.g. John Doe" },
    { key: "guardian", label: "7. Guardian for minor children (if applicable)", placeholder: "e.g. Sarah Smith, or N/A" },
    { key: "specialBequests", label: "8. Special bequests", placeholder: "e.g. My wedding ring to my daughter Emily, or None", multiline: true },
  ];

  return (
    <div style={S.draftForm}>
      {fields.map(({ key, label, placeholder, multiline }) => (
        <div key={key}>
          <label style={S.formLabel}>{label}</label>
          {multiline ? (
            <textarea
              style={{ ...S.formInput, minHeight: 60, resize: "vertical" }}
              value={inputs[key]}
              onChange={(e) => update(key, e.target.value)}
              placeholder={placeholder}
              rows={3}
            />
          ) : (
            <input
              style={S.formInput}
              value={inputs[key]}
              onChange={(e) => update(key, e.target.value)}
              placeholder={placeholder}
            />
          )}
        </div>
      ))}
      <button
        style={{
          ...S.submitBtn,
          ...(loading ? S.submitBtnDisabled : {}),
        }}
        onClick={onGenerate}
        disabled={loading || !inputs.fullName.trim()}
      >
        {loading ? "Generating..." : "Generate Draft Will"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WillsTrustsExplainer() {
  const [searchParams] = useSearchParams();
  const entitiesParam = searchParams.get("entities");
  const entities = entitiesParam ? JSON.parse(entitiesParam) : {};

  const [subType, setSubType] = useState<SubType>("will");
  const [situation, setSituation] = useState(entities.situation_text || "");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [rawChunks, setRawChunks] = useState("");
  const [response, setResponse] = useState<Partial<WillsTrustsResponse>>({});
  const [chatOpen, setChatOpen] = useState(false);

  // Draft-specific state
  const [draftInputs, setDraftInputs] = useState<DraftInputs>(INITIAL_DRAFT);
  const [generatedDraft, setGeneratedDraft] = useState("");

  const abortRef = useRef<AbortController | null>(null);

  // ── SSE fetch ──
  const handleExplain = useCallback(async (draftSituation?: string) => {
    const sit = draftSituation || situation;
    if (!sit.trim()) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStreaming(true);
    setError("");
    setRawChunks("");
    setResponse({});

    try {
      const resp = await fetch(
        `${import.meta.env.VITE_API_URL || ""}/api/wills-trusts/explain`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            situation: sit,
            sub_type: subType,
            language: "en",
          }),
          signal: controller.signal,
        },
      );

      if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response stream");

      let full = "";
      for await (const raw of readSSE(reader)) {
        try {
          const data = JSON.parse(raw);
          if (data.chunk) {
            full += data.chunk;
            setRawChunks(full);
            try { setResponse(JSON.parse(full)); } catch { /* partial */ }
          }
          if (data.disclaimer) {
            setResponse((p) => ({ ...p, disclaimer: data.disclaimer }));
          }
          if (data.error) {
            setError(data.message || "Something went wrong.");
            break;
          }
          if (data.done) break;
        } catch { /* skip */ }
      }

      // Final parse
      try {
        const parsed = JSON.parse(full);
        setResponse(parsed);
        if (parsed.draft_content) {
          setGeneratedDraft(parsed.draft_content);
        }
      } catch {
        if (!full.trim() && !error) setError("Could not parse explanation. Please try again.");
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Connection failed");
    } finally {
      setStreaming(false);
    }
  }, [situation, subType, error]);

  // ── Draft generation ──
  const handleGenerateDraft = useCallback(() => {
    const draftSituation = [
      `Draft a Florida-compliant will for:`,
      `Name: ${draftInputs.fullName}`,
      `Marital status: ${draftInputs.maritalStatus}`,
      `Spouse: ${draftInputs.spouseName || "N/A"}`,
      `Children: ${draftInputs.children || "None"}`,
      `Assets: ${draftInputs.assets}`,
      `Beneficiaries: ${draftInputs.beneficiaries}`,
      `Executor: ${draftInputs.executor}`,
      `Guardian for minors: ${draftInputs.guardian || "N/A"}`,
      `Special bequests: ${draftInputs.specialBequests || "None"}`,
    ].join("\n");
    handleExplain(draftSituation);
  }, [draftInputs, handleExplain]);

  // ── Download draft ──
  const handleDownload = useCallback(() => {
    const content = generatedDraft || response.draft_content || "";
    if (!content) return;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "florida_will_draft.txt";
    a.click();
    URL.revokeObjectURL(url);
  }, [generatedDraft, response.draft_content]);

  return (
    <div style={S.page}>
      <header style={S.header}>
        <Link to="/" style={S.back}>← Back to LegalClear</Link>
        <h1 style={S.h1}>Wills & Trusts</h1>
        <p style={S.sub}>Wills, trusts & probate explained</p>
      </header>

      {/* Sub-type tabs */}
      <div style={S.tabs}>
        {SUB_TYPES.map((st) => (
          <button
            key={st}
            style={S.tab(subType === st)}
            onClick={() => {
              setSubType(st);
              setResponse({});
              setRawChunks("");
              setGeneratedDraft("");
            }}
          >
            {SUB_LABELS[st]}
          </button>
        ))}
      </div>

      {/* Situation textarea (hidden for draft_will when form is shown) */}
      {subType !== "draft_will" && (
        <>
          <textarea
            style={S.textarea}
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            placeholder={
              subType === "will"
                ? "Describe your will-related situation. E.g. 'I want to write a will leaving my house to my children.'"
                : subType === "trust"
                ? "Describe your trust-related situation. E.g. 'I want to set up a living trust to avoid probate.'"
                : "Describe your probate situation. E.g. 'My father passed away without a will and I need to handle his estate.'"
            }
            rows={3}
          />
          <button
            style={{
              ...S.submitBtn,
              ...(streaming || !situation.trim() ? S.submitBtnDisabled : {}),
            }}
            onClick={() => handleExplain()}
            disabled={streaming || !situation.trim()}
          >
            {streaming ? "Getting explanation..." : "Get Explanation"}
          </button>
        </>
      )}

      {/* Draft Will form */}
      {subType === "draft_will" && !generatedDraft && !response.draft_content && (
        <DraftForm
          inputs={draftInputs}
          onChange={setDraftInputs}
          onGenerate={handleGenerateDraft}
          loading={streaming}
        />
      )}

      {/* Error */}
      {error && <p style={S.error}>{error}</p>}

      {/* Streaming indicator */}
      {streaming && !response.what_this_means && (
        <p style={S.loading}>Analyzing your situation…</p>
      )}

      {/* Raw streaming fallback */}
      {streaming && rawChunks && !response.what_this_means && (
        <p style={{ ...S.bodyText, color: "#6B7280" }}>
          {rawChunks.slice(0, 300)}…
        </p>
      )}

      {/* Response panel */}
      {(response.what_this_means || response.draft_content || generatedDraft) && (
        <div style={S.responsePanel}>
          {response.sub_type_identified && (
            <div style={{
              display: "inline-block",
              padding: "4px 12px",
              background: "#EEF2FF",
              borderRadius: 12,
              fontSize: 12,
              fontWeight: 600,
              color: "#4361EE",
              marginBottom: 12,
            }}>
              {response.sub_type_identified}
            </div>
          )}

          {/* What this means */}
          {response.what_this_means && (
            <>
              <h2 style={S.sTitle}>What This Means</h2>
              <p style={S.bodyText}>{response.what_this_means}</p>
            </>
          )}

          {/* Florida requirements — blue cards */}
          {response.florida_requirements && response.florida_requirements.length > 0 && (
            <>
              <h2 style={S.sTitle}>Florida Requirements</h2>
              {response.florida_requirements.map((r, i) => (
                <div key={i} style={S.blueCard}>📘 {r}</div>
              ))}
            </>
          )}

          {/* Typical process */}
          {response.typical_process && (
            <>
              <h2 style={S.sTitle}>Typical Process</h2>
              <p style={S.bodyText}>{response.typical_process}</p>
            </>
          )}

          {/* Probate implications */}
          {response.probate_implications && (
            <>
              <h2 style={S.sTitle}>Probate Implications</h2>
              <p style={S.bodyText}>{response.probate_implications}</p>
            </>
          )}

          {/* Useful documents */}
          {response.useful_documents && response.useful_documents.length > 0 && (
            <>
              <h2 style={S.sTitle}>Useful Documents</h2>
              {response.useful_documents.map((d, i) => (
                <div key={i} style={S.blueCard}>📄 {d}</div>
              ))}
            </>
          )}

          {/* Watch out for — amber cards */}
          {response.watch_out_for && response.watch_out_for.length > 0 && (
            <>
              <h2 style={S.sTitle}>Watch Out For</h2>
              {response.watch_out_for.map((w, i) => (
                <div key={i} style={S.amberCard}>⚠️ {w}</div>
              ))}
            </>
          )}

          {/* Draft content */}
          {(response.draft_content || generatedDraft) && (
            <>
              <h2 style={S.sTitle}>Draft Will</h2>
              <div style={S.draftDoc}>
                {response.draft_content || generatedDraft}
              </div>
              <button style={S.downloadBtn} onClick={handleDownload}>
                📥 Download as .txt
              </button>
            </>
          )}
        </div>
      )}

      {/* Disclaimer */}
      <div style={S.disc}>
        {response.disclaimer ||
          "LegalClear provides legal information, not legal advice. Nothing here creates an attorney-client relationship. Consult a licensed Florida attorney for your specific situation."}
      </div>

      {/* Chat system */}
      <ChatButton module="wills_trusts" onClick={() => setChatOpen(true)} />
      {chatOpen && (
        <ChatDrawer
          module="wills_trusts"
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
        />
      )}
    </div>
  );
}
