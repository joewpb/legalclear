/**
 * Court Forms Finder (FL) — live, data-driven.
 *
 * Surfaces the published court_forms library from the backend:
 *   GET  /api/forms/facets               → category dropdown
 *   GET  /api/forms/search               → keyword + category search (paginated)
 *   POST /api/forms/suggest (SSE)        → AI form suggestions for a situation
 *   GET  /api/forms/{form_number}        → PDF stream (opened in a new tab)
 *
 * All forms are valid statewide; there is no county filter. Filters are
 * category + keyword only.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const API_BASE =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
const API_KEY = (import.meta as any).env?.VITE_API_KEY || "testkey123";
const PAGE_SIZE = 20;
const FALLBACK_DISCLAIMER =
  "This tool provides legal information only, not legal advice.";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FormRow = {
  form_number: string;
  title: string;
  category: string | null;
  plain_language_summary: string | null;
  situation_tags: string[] | null;
  source_page_url: string | null;
  status: string;
};

type Facet = { value: string; count: number };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Decode an SSE byte stream into the string payload of each `data:` line. */
async function* readSSE(r: ReadableStreamDefaultReader<Uint8Array>) {
  const d = new TextDecoder();
  let b = "";
  while (true) {
    const { done, value } = await r.read();
    if (done) break;
    b += d.decode(value, { stream: true });
    const ls = b.split("\n");
    b = ls.pop() ?? "";
    for (const l of ls) if (l.startsWith("data: ")) yield l.slice(6);
  }
}

/**
 * Client-side safety net: the backend enforces third-person output, but never
 * render second-person directives even if a chunk slips through. Runs over the
 * full accumulated text so it is robust to chunk boundaries.
 */
function stripSecondPerson(t: string): string {
  return t
    .replace(/\byou should\b/gi, "a filer may")
    .replace(/\byou must\b/gi, "a filer is expected to")
    .replace(/\byou need to\b/gi, "a filer may need to")
    .replace(/\byou(?:'| a)?re\b/gi, "a filer is")
    .replace(/\byou(?:'ll| will)\b/gi, "a filer may")
    .replace(/\byou(?:'ve| have)\b/gi, "a filer has")
    .replace(/\byou (can|may|might|could|would)\b/gi, "a filer $1")
    .replace(/\byourself\b/gi, "themselves")
    .replace(/\byours\b/gi, "theirs")
    .replace(/\byour\b/gi, "the")
    .replace(/\byou\b/gi, "a filer");
}

/** Turn a category slug ("family_law_support") into a label. */
function prettyCategory(slug: string): string {
  return slug
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Build a PDF URL, encoding each path segment but preserving "/". */
function pdfUrl(formNumber: string): string {
  const encoded = formNumber.split("/").map(encodeURIComponent).join("/");
  return `${API_BASE}/api/forms/${encoded}`;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  page: {
    maxWidth: "var(--max-page)",
    margin: "0 auto",
    padding: "var(--space-2)",
  } as React.CSSProperties,
  header: { padding: "var(--space-2) 0" } as React.CSSProperties,
  back: {
    color: "var(--muted)",
    fontSize: 12,
    textDecoration: "none",
  } as React.CSSProperties,
  h1: {
    fontFamily: "var(--font-serif)",
    fontSize: 24,
    fontWeight: 500,
    margin: "8px 0 4px",
  } as React.CSSProperties,
  sub: { color: "var(--muted)", fontSize: 14, margin: 0 } as React.CSSProperties,
  section: { marginTop: "var(--space-3)" } as React.CSSProperties,
  sTitle: {
    fontFamily: "var(--font-serif)",
    fontSize: 18,
    fontWeight: 500,
    margin: "0 0 12px",
  } as React.CSSProperties,
  textarea: {
    width: "100%",
    minHeight: 90,
    padding: 12,
    border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)",
    fontSize: 15,
    lineHeight: 1.5,
    fontFamily: "inherit",
    resize: "vertical",
    boxSizing: "border-box",
  } as React.CSSProperties,
  btn: {
    padding: "12px 18px",
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: "var(--radius)",
    fontSize: 15,
    fontWeight: 500,
    cursor: "pointer",
  } as React.CSSProperties,
  btnGhost: {
    padding: "12px 18px",
    background: "#fff",
    color: "var(--accent)",
    border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
  } as React.CSSProperties,
  panel: {
    background: "#fff",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "var(--space-2)",
    marginTop: 12,
  } as React.CSSProperties,
  aiBody: {
    fontSize: 15,
    lineHeight: 1.7,
    margin: 0,
    whiteSpace: "pre-wrap",
  } as React.CSSProperties,
  disc: {
    marginTop: 12,
    padding: "var(--space-2)",
    background: "#f5f5f5",
    borderLeft: "3px solid var(--muted)",
    fontSize: 12,
    lineHeight: 1.6,
    color: "var(--muted)",
  } as React.CSSProperties,
  controls: {
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
    alignItems: "stretch",
  } as React.CSSProperties,
  input: {
    flex: "1 1 180px",
    padding: "10px 12px",
    border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)",
    fontSize: 14,
    fontFamily: "inherit",
    boxSizing: "border-box",
  } as React.CSSProperties,
  select: {
    flex: "1 1 180px",
    padding: "10px 12px",
    border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)",
    fontSize: 14,
    fontFamily: "inherit",
    background: "#fff",
    boxSizing: "border-box",
  } as React.CSSProperties,
  card: {
    background: "#fff",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "var(--space-2)",
    marginBottom: 12,
    display: "grid",
    gap: 6,
  } as React.CSSProperties,
  cardNum: {
    fontFamily: "var(--font-mono, monospace)",
    fontSize: 12,
    color: "var(--muted)",
    margin: 0,
  } as React.CSSProperties,
  cardTitle: { fontSize: 16, fontWeight: 600, margin: 0 } as React.CSSProperties,
  summary: {
    fontSize: 14,
    lineHeight: 1.6,
    color: "#333",
    margin: "2px 0",
  } as React.CSSProperties,
  clamp: {
    display: "-webkit-box",
    WebkitLineClamp: 3,
    WebkitBoxOrient: "vertical",
    overflow: "hidden",
  } as React.CSSProperties,
  chips: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 2 } as React.CSSProperties,
  chip: {
    background: "#EEF2FF",
    border: "1px solid var(--border)",
    borderRadius: 999,
    padding: "2px 10px",
    fontSize: 12,
    color: "#3A0CA3",
  } as React.CSSProperties,
  cardBtns: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 } as React.CSSProperties,
  linkBtn: {
    padding: "8px 12px",
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: "var(--radius)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    textDecoration: "none",
  } as React.CSSProperties,
  copyBtn: {
    padding: "8px 12px",
    background: "#fff",
    color: "var(--accent)",
    border: "1px solid var(--border-strong)",
    borderRadius: "var(--radius)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
  } as React.CSSProperties,
  moreBtn: {
    background: "none",
    border: "none",
    color: "var(--accent)",
    fontSize: 13,
    cursor: "pointer",
    padding: 0,
    justifySelf: "start",
  } as React.CSSProperties,
  pager: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginTop: 12,
  } as React.CSSProperties,
  skel: {
    background: "linear-gradient(90deg,#eee,#f5f5f5,#eee)",
    borderRadius: "var(--radius)",
    height: 96,
    marginBottom: 12,
  } as React.CSSProperties,
  empty: {
    textAlign: "center",
    color: "var(--muted)",
    padding: "var(--space-3)",
    fontSize: 14,
  } as React.CSSProperties,
  err: { color: "#C62828", fontSize: 14, marginTop: 8 } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Result card
// ---------------------------------------------------------------------------

function ResultCard({ form }: { form: FormRow }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const summary = form.plain_language_summary || "";
  const tags = form.situation_tags || [];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(form.form_number);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — no-op */
    }
  };

  return (
    <article style={S.card}>
      <p style={S.cardNum}>{form.form_number}</p>
      <h3 style={S.cardTitle}>{form.title}</h3>
      {summary && (
        <p style={{ ...S.summary, ...(expanded ? {} : S.clamp) }}>{summary}</p>
      )}
      {summary.length > 160 && (
        <button
          type="button"
          style={S.moreBtn}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
      {tags.length > 0 && (
        <div style={S.chips}>
          {tags.map((t) => (
            <span key={t} style={S.chip}>
              {t}
            </span>
          ))}
        </div>
      )}
      <div style={S.cardBtns}>
        <a
          href={pdfUrl(form.form_number)}
          target="_blank"
          rel="noopener noreferrer"
          style={S.linkBtn}
        >
          View PDF
        </a>
        <button type="button" style={S.copyBtn} onClick={copy}>
          {copied ? "Copied ✓" : "Copy Form Number"}
        </button>
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FormsFinderFL() {
  // ── Browse / filter state ──
  const [categories, setCategories] = useState<Facet[]>([]);
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [results, setResults] = useState<FormRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchError, setSearchError] = useState<string | null>(null);

  // ── AI situation state ──
  const [situation, setSituation] = useState("");
  const [aiText, setAiText] = useState("");
  const [aiDisclaimer, setAiDisclaimer] = useState("");
  const [aiStreaming, setAiStreaming] = useState(false);
  const [aiStarted, setAiStarted] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // ── Data fetching ──
  const runSearch = useCallback(
    async (q: string, cat: string, off: number) => {
      setLoading(true);
      setSearchError(null);
      try {
        const params: Record<string, string | number> = {
          limit: PAGE_SIZE,
          offset: off,
        };
        if (q.trim()) params.q = q.trim();
        if (cat) params.category = cat;
        const { data } = await api.get("/api/forms/search", { params });
        setResults(data.forms || []);
        setTotal(data.total || 0);
        setOffset(off);
      } catch {
        setResults([]);
        setTotal(0);
        setSearchError("Could not load forms. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // On load: facets + initial unfiltered results.
  useEffect(() => {
    api
      .get("/api/forms/facets")
      .then(({ data }) => setCategories(data.categories || []))
      .catch(() => setCategories([]));
    runSearch("", "", 0);
  }, [runSearch]);

  const onSearch = () => runSearch(keyword, category, 0);
  const onClear = () => {
    setKeyword("");
    setCategory("");
    runSearch("", "", 0);
  };

  // ── AI suggestion (SSE) ──
  const findRelevant = useCallback(async () => {
    if (situation.trim().length <= 20) return;
    setAiStreaming(true);
    setAiStarted(true);
    setAiError(null);
    setAiText("");
    setAiDisclaimer("");
    try {
      const res = await fetch(`${API_BASE}/api/forms/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ situation: situation.trim() }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      let full = "";
      for await (const c of readSSE(reader)) {
        if (c === "[DONE]") break;
        try {
          const obj = JSON.parse(c);
          if (obj.error) {
            setAiError(obj.message || "Suggestions could not be generated.");
            if (obj.disclaimer) setAiDisclaimer(obj.disclaimer);
            continue;
          }
          if (obj.disclaimer) {
            setAiDisclaimer(obj.disclaimer);
            continue;
          }
          if (typeof obj.text === "string") {
            full += obj.text;
            setAiText(full);
          }
        } catch {
          /* ignore non-JSON keepalive lines */
        }
      }
    } catch (e: any) {
      setAiError(e?.message || "Suggestions could not be generated.");
    } finally {
      setAiStreaming(false);
    }
  }, [situation]);

  const canSubmit = situation.trim().length > 20 && !aiStreaming;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <div style={S.page}>
      <header style={S.header}>
        <Link to="/" style={S.back}>
          ← Back to hub
        </Link>
        <h1 style={S.h1}>Court Forms (FL)</h1>
        <p style={S.sub}>
          Search official Florida court forms, or describe a situation to find
          relevant ones.
        </p>
      </header>

      {/* ── Section 1 — AI situation search ── */}
      <section style={S.section}>
        <h2 style={S.sTitle}>Find forms by situation</h2>
        <textarea
          style={S.textarea}
          placeholder="Describe your situation in plain English..."
          value={situation}
          onChange={(e) => setSituation(e.target.value)}
        />
        <div style={{ marginTop: 10 }}>
          <button
            type="button"
            style={{ ...S.btn, opacity: canSubmit ? 1 : 0.5 }}
            disabled={!canSubmit}
            onClick={findRelevant}
          >
            {aiStreaming ? "Finding…" : "Find Relevant Forms"}
          </button>
        </div>

        {aiStarted && (
          <div style={S.panel}>
            {aiError && <p style={S.err}>{aiError}</p>}
            <p style={S.aiBody}>
              {stripSecondPerson(aiText)}
              {aiStreaming && !aiText && "Reviewing the forms library…"}
            </p>
            <div style={S.disc}>{aiDisclaimer || FALLBACK_DISCLAIMER}</div>
          </div>
        )}
      </section>

      {/* ── Section 2 — Browse and filter ── */}
      <section style={S.section}>
        <h2 style={S.sTitle}>Browse and filter</h2>
        <div style={S.controls}>
          <input
            style={S.input}
            type="text"
            placeholder="Search by keyword…"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSearch();
            }}
          />
          <select
            style={S.select}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.value} value={c.value}>
                {prettyCategory(c.value)} ({c.count})
              </option>
            ))}
          </select>
          <button type="button" style={S.btn} onClick={onSearch}>
            Search
          </button>
          <button type="button" style={S.btnGhost} onClick={onClear}>
            Clear filters
          </button>
        </div>
      </section>

      {/* ── Section 3 — Results ── */}
      <section style={S.section}>
        {searchError && <p style={S.err}>{searchError}</p>}

        {loading ? (
          <>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} style={S.skel} />
            ))}
          </>
        ) : results.length === 0 ? (
          <p style={S.empty}>
            No forms found. Try different keywords or filters.
          </p>
        ) : (
          <>
            {results.map((f) => (
              <ResultCard key={f.form_number} form={f} />
            ))}
            <div style={S.pager}>
              <button
                type="button"
                style={{ ...S.btnGhost, opacity: offset === 0 ? 0.5 : 1 }}
                disabled={offset === 0}
                onClick={() =>
                  runSearch(keyword, category, Math.max(0, offset - PAGE_SIZE))
                }
              >
                ← Prev
              </button>
              <span style={{ fontSize: 13, color: "var(--muted)" }}>
                {pageStart}–{pageEnd} of {total}
              </span>
              <button
                type="button"
                style={{
                  ...S.btnGhost,
                  opacity: pageEnd >= total ? 0.5 : 1,
                }}
                disabled={pageEnd >= total}
                onClick={() => runSearch(keyword, category, offset + PAGE_SIZE)}
              >
                Next →
              </button>
            </div>
          </>
        )}
      </section>

      <footer className="page-disclaimer" style={{ marginTop: "var(--space-3)" }}>
        <p>
          LegalClear provides legal information, not legal advice. Forms are
          official Florida court forms. Using this site does not create an
          attorney-client relationship.
        </p>
      </footer>
    </div>
  );
}
