/**
 * I-5 — Claim Guide page (Phase I finale, 2026-08-23).
 *
 * The claim state machine UI: create or resume a claim, see the phase
 * timeline with three-list content, record what happened, answer red-flag
 * questions, download artifacts, and use the explicit LLM taps.
 *
 * Hard rules honored here:
 *   - ZERO client-side date math. Every date is rendered verbatim from the
 *     backend (deadline engine output). "Day N" and "Phase X of Y" come
 *     from the backend state payload.
 *   - No directives in static copy — third-person/informational framing.
 *   - The persistent, non-dismissible disclaimer renders on every view.
 *   - Decision 16: English only. No language parameter, no ES paths.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PersistentDisclaimer from "../components/PersistentDisclaimer";

// ---------------------------------------------------------------------------
// Types (backend contract — property names are the API's, verbatim)
// ---------------------------------------------------------------------------

interface PhasePayload {
  phase_id: string;
  sequence: number;
  status: "active" | "completed" | "upcoming";
  extended: boolean;
  title: string;
  plain_summary: string;
  do_now: { id: string; text: string; artifact?: string | null; why: string; consequence?: string | null }[];
  never_do: { id: string; text: string; consequence: string; reasonable_inaction?: string | null }[];
  watch_for: { id: string; signal: string; escalates_to: string }[];
  documents: string[];
  authority: string[];
  effective_date: string;
}

interface StatePayload {
  peril: string;
  date_of_loss: string | null;
  phase_count: number;
  current_phase: string | null;
  current_sequence: number | null;
  day_number: number | null;
  phases: {
    phase_id: string; sequence: number; status: string;
    entered_at: string | null; exited_at: string | null;
    typical_window_days: number[] | null; extended: boolean;
  }[];
  active_phase_ids: string[];
  completed_phase_ids: string[];
}

interface DeadlineItem {
  label: string; due_date: string; governing_rule: string;
  severity: string; consequence: string; is_past: boolean;
  deadline_type: string; computation_trace: Record<string, unknown>[];
}

interface RedFlag { name: string; label: string; description: string; source: string }

interface GuidePayload {
  peril: string;
  state: StatePayload;
  phases: PhasePayload[];
  deadlines: DeadlineItem[];
  due_this_week: DeadlineItem[];
  claim_regime: { regime: "pre" | "post" | "unknown"; guidance?: string };
  red_flags: RedFlag[];
  red_flag_catalog: RedFlag[];
  escalation: {
    type: string; active_count: number; flags: RedFlag[]; banner: string;
    show_financial_screen: boolean; financial_screen_text: string | null;
    resource_links: { label: string; url: string }[];
  } | null;
  details: Record<string, string>;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BASE = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
const CODE_KEY = "lc_claim_code";
const SESSION_KEY = "lc_claim_session";

const PERILS: Record<string, string> = {
  fire: "Fire", smoke: "Smoke", water: "Water (burst pipe / appliance)",
  wind: "Wind", hurricane: "Hurricane", flood: "Flood", theft: "Theft",
  sinkhole: "Sinkhole", tree_fall: "Tree fall", mold: "Mold",
  condo: "Condo", vandalism: "Vandalism",
};

const EVENT_LABELS: Record<string, string> = {
  claim_number_received: "I received my claim number",
  adjuster_inspection_scheduled: "An inspection has been scheduled",
  carrier_estimate_received: "I received the carrier's estimate",
  contents_inventory_submitted: "I submitted my contents inventory",
  payment_received: "I received a payment",
  rebuild_complete: "Rebuilding is complete",
  claim_denied_or_underpaid: "My claim was denied or underpaid",
  resolved_or_suit_filed: "The dispute is resolved (or suit filed)",
};

const DETAIL_FIELDS: { key: string; label: string }[] = [
  { key: "insured_name", label: "Your name" },
  { key: "insured_address", label: "Your address" },
  { key: "property_address", label: "Property address" },
  { key: "insurer_name", label: "Insurance company" },
  { key: "claim_number", label: "Claim number" },
  { key: "policy_number", label: "Policy number" },
  { key: "adjuster_name", label: "Adjuster name" },
  { key: "fire_report_number", label: "Fire report number" },
  { key: "mortgage_company", label: "Mortgage company" },
  { key: "phone_number", label: "Phone number" },
];

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const TOUCH_MIN = 48;

const S = {
  page: { maxWidth: "var(--max-page)", margin: "0 auto", padding: "var(--space-2)" } as React.CSSProperties,
  h1: { fontFamily: "var(--font-serif)", fontSize: 24, fontWeight: 500, margin: "8px 0 4px" } as React.CSSProperties,
  sub: { color: "var(--muted)", fontSize: 14, margin: 0 } as React.CSSProperties,
  card: { background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--radius)",
    padding: "var(--space-2)", marginBottom: "var(--space-2)" } as React.CSSProperties,
  btn: { display: "block", width: "100%", minHeight: TOUCH_MIN, padding: "0 16px",
    background: "var(--accent)", color: "#fff", border: "none", borderRadius: "var(--radius)",
    fontSize: 15, fontWeight: 500, cursor: "pointer", marginBottom: "var(--space-2)" } as React.CSSProperties,
  btnGhost: { display: "block", width: "100%", minHeight: TOUCH_MIN, padding: "0 16px",
    background: "#fff", color: "var(--accent)", border: "1px solid var(--accent)",
    borderRadius: "var(--radius)", fontSize: 15, fontWeight: 500, cursor: "pointer",
    marginBottom: "var(--space-2)" } as React.CSSProperties,
  input: { width: "100%", minHeight: TOUCH_MIN, padding: "0 12px", fontSize: 15,
    border: "1px solid var(--border-strong)", borderRadius: "var(--radius)",
    boxSizing: "border-box" as const, marginBottom: "var(--space-2)" } as React.CSSProperties,
  label: { display: "block", fontSize: 13, color: "var(--muted)", marginBottom: 4 } as React.CSSProperties,
  listItem: { display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 0",
    borderBottom: "1px solid var(--border)", fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  checkBox: { width: TOUCH_MIN, height: TOUCH_MIN, border: "2px solid var(--border-strong)",
    borderRadius: 3, flexShrink: 0, display: "flex", alignItems: "center",
    justifyContent: "center", fontSize: 16, color: "var(--accent)",
    cursor: "pointer", background: "#fff", fontWeight: 700 } as React.CSSProperties,
  err: { background: "#FFEBEE", border: "1px solid #C62828", borderRadius: "var(--radius)",
    padding: "10px 12px", marginBottom: 12, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  warn: { background: "#FFF8E1", border: "1px solid #F57F17", borderRadius: "var(--radius)",
    padding: "12px 14px", marginBottom: 8, fontSize: 14, lineHeight: 1.5 } as React.CSSProperties,
  badge: (color: string): React.CSSProperties => ({ display: "inline-block", padding: "2px 10px",
    borderRadius: "var(--radius)", fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
    textTransform: "uppercase" as const, background: color, color: "#fff", marginRight: 6 }),
  progressTrack: { height: 10, background: "#E8E8E3", borderRadius: 5,
    overflow: "hidden", margin: "12px 0 4px" } as React.CSSProperties,
  progressFill: (pct: number): React.CSSProperties => ({ height: 10, width: `${pct}%`,
    background: "var(--accent)", borderRadius: 5 }),
};

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------

function DeadlinesPanel({ deadlines, dueThisWeek }: { deadlines: DeadlineItem[]; dueThisWeek: DeadlineItem[] }) {
  if (deadlines.length === 0) return null;
  return (
    <section style={S.card}>
      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "0 0 4px" }}>
        Deadlines
      </h2>
      <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
        Computed by the deadline engine from your claim facts. Verify each against the
        governing source shown under it.
      </p>
      {dueThisWeek.length > 0 && (
        <div style={{ background: "#FFFDE7", border: "1px solid #F57F17", borderRadius: "var(--radius)",
          padding: "10px 12px", marginBottom: 12 }}>
          <strong style={{ fontSize: 14 }}>Due this week:</strong>
          {dueThisWeek.map((d) => (
            <div key={d.label} style={{ fontSize: 14, marginTop: 6 }}>
              {d.label} — <strong>{d.due_date}</strong>
            </div>
          ))}
        </div>
      )}
      {deadlines.map((d) => (
        <div key={d.label + d.due_date} style={{ border: "1px solid var(--border)",
          borderRadius: "var(--radius)", padding: 12, marginBottom: 10,
          background: d.is_past ? "#FFEBEE" : "#FAFAFA", opacity: d.is_past ? 0.75 : 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{d.label}</div>
          <div style={{ fontSize: 20, fontWeight: 600, fontFamily: "var(--mono-font, monospace)", margin: "4px 0" }}>
            {d.due_date} {d.is_past && <span style={S.badge("#C62828")}>past</span>}
          </div>
          <div style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono-font, monospace)" }}>
            {d.governing_rule}
          </div>
          {d.consequence && <p style={{ fontSize: 13, margin: "6px 0 0", color: "var(--fg-secondary, #555)" }}>{d.consequence}</p>}
        </div>
      ))}
    </section>
  );
}

function PhaseCard({ phase, active }: { phase: PhasePayload; active: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const shown = (list: unknown[]) => (expanded ? list : list.slice(0, 3));
  return (
    <section style={{ ...S.card, borderColor: active ? "var(--accent)" : "var(--border)",
      borderWidth: active ? 2 : 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
        {active && <span style={S.badge("#2E7D32")}>current</span>}
        {phase.status === "completed" && <span style={S.badge("#6B6B66")}>done</span>}
        <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: 0, flex: 1 }}>
          {phase.title}
        </h2>
      </div>
      <p style={{ fontSize: 14, lineHeight: 1.6, margin: "0 0 8px" }}>{phase.plain_summary}</p>
      {phase.extended && (
        <div style={S.warn}>
          This phase is taking longer than its typical window. Everything below still helps —
          none of it depends on having started it on time.
        </div>
      )}

      {phase.do_now.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, margin: "12px 0 4px" }}>Do now</h3>
          {shown(phase.do_now).map((item: PhasePayload["do_now"][number]) => (
            <div key={item.id} style={S.listItem}>
              <div style={{ flex: 1 }}>
                <div>{item.text}</div>
                {item.why && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>Why: {item.why}</div>}
              </div>
            </div>
          ))}
        </>
      )}
      {phase.never_do.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, margin: "12px 0 4px" }}>Avoid</h3>
          {shown(phase.never_do).map((item: PhasePayload["never_do"][number]) => (
            <div key={item.id} style={S.listItem}>
              <div style={{ flex: 1 }}>
                <div>{item.text}</div>
                {item.consequence && (
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                    What can happen: {item.consequence}
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}
      {phase.watch_for.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, margin: "12px 0 4px" }}>Watch for</h3>
          {shown(phase.watch_for).map((item: PhasePayload["watch_for"][number]) => (
            <div key={item.id} style={S.listItem}>
              <div style={{ flex: 1 }}>
                <div>{item.signal}</div>
                {item.escalates_to && (
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                    If this happens, the guide escalates: {item.escalates_to}
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}
      {phase.documents.length > 0 && (
        <p style={{ fontSize: 13, margin: "10px 0 0" }}>
          <strong>Documents to save:</strong> {phase.documents.join(" · ")}
        </p>
      )}
      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
        {phase.authority.join(" · ")} · effective {phase.effective_date}
      </div>
      {(phase.do_now.length > 3 || phase.never_do.length > 3 || phase.watch_for.length > 3) && (
        <button style={{ ...S.btnGhost, marginTop: 8, marginBottom: 0 }}
          onClick={() => setExpanded(!expanded)}>
          {expanded ? "Show fewer" : "Show all items"}
        </button>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ClaimGuide() {
  const [code, setCode] = useState<string | null>(() => localStorage.getItem(CODE_KEY));
  const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem(SESSION_KEY));
  const [guide, setGuide] = useState<GuidePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inceptionNeeded, setInceptionNeeded] = useState(false);

  // ── create ──
  const [peril, setPeril] = useState("fire");
  const [lossDate, setLossDate] = useState("");
  const [resumeCode, setResumeCode] = useState("");

  const fetchGuide = useCallback(async (claimCode: string) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/claims/${claimCode}/guide`);
      if (r.status === 404) {
        localStorage.removeItem(CODE_KEY);
        localStorage.removeItem(SESSION_KEY);
        setCode(null);
        setError("No claim found for that code.");
        return;
      }
      if (!r.ok) {
        setError(`Could not load the guide (HTTP ${r.status}).`);
        return;
      }
      setGuide(await r.json());
    } catch {
      setError("Could not reach the guide service.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (code) fetchGuide(code);
  }, [code, fetchGuide]);

  const createClaim = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/claims`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ peril, date_of_loss: lossDate || null }),
      });
      if (!r.ok) {
        setError(`Could not create the claim (HTTP ${r.status}).`);
        return;
      }
      const data = await r.json();
      localStorage.setItem(CODE_KEY, data.code);
      localStorage.setItem(SESSION_KEY, data.session_id);
      setCode(data.code);
      setSessionId(data.session_id);
      setInceptionNeeded(true);
    } catch {
      setError("Could not reach the claim service.");
    } finally {
      setBusy(false);
    }
  };

  const saveInception = async (value: string | null) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/property-casualty/facts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          policy_inception_date: value,
        }),
      });
      if (!r.ok) {
        setError(`Could not save the policy date (HTTP ${r.status}).`);
        return;
      }
      setInceptionNeeded(false);
      if (code) fetchGuide(code);
    } catch {
      setError("Could not reach the claim service.");
    } finally {
      setBusy(false);
    }
  };

  const recordEvent = async (triggerName: string) => {
    if (!code) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/claims/${code}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trigger_name: triggerName }),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => null);
        setError(detail?.detail || `Could not record the event (HTTP ${r.status}).`);
        return;
      }
      fetchGuide(code);
    } catch {
      setError("Could not reach the claim service.");
    } finally {
      setBusy(false);
    }
  };

  const downloadArtifact = async (artifactId: string) => {
    if (!code) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/claims/${code}/artifacts/${artifactId}`);
      if (!r.ok) {
        setError(`Could not build that document (HTTP ${r.status}).`);
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${artifactId}.${artifactId.endsWith("csv") ? "csv" : artifactId.endsWith("ics") ? "ics" : "pdf"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not download the document.");
    } finally {
      setBusy(false);
    }
  };

  const saveDetails = async (details: Record<string, string>) => {
    if (!code) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/api/claims/${code}/details`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ details }),
      });
      if (!r.ok) {
        setError(`Could not save the details (HTTP ${r.status}).`);
        return;
      }
      fetchGuide(code);
    } catch {
      setError("Could not reach the claim service.");
    } finally {
      setBusy(false);
    }
  };

  // ── views ──

  if (!code) {
    return (
      <div style={S.page}>
        <h1 style={S.h1}>Claim Guide</h1>
        <p style={S.sub}>A timeline that walks a property claim from the first day to resolution.</p>
        {error && <div style={S.err}>{error}</div>}
        <div style={S.card}>
          <h2 style={{ fontSize: 16, margin: "0 0 12px" }}>Start a claim guide</h2>
          <label style={S.label}>What happened</label>
          <select style={S.input} value={peril} onChange={(e) => setPeril(e.target.value)}>
            {Object.entries(PERILS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <label style={S.label}>Date of loss (optional)</label>
          <input style={S.input} type="date" value={lossDate}
            onChange={(e) => setLossDate(e.target.value)} />
          <button style={S.btn} disabled={busy} onClick={createClaim}>
            {busy ? "Working…" : "Create my claim guide"}
          </button>
        </div>
        <div style={S.card}>
          <h2 style={{ fontSize: 16, margin: "0 0 12px" }}>Resume with your claim code</h2>
          <input style={S.input} placeholder="Paste your claim code"
            value={resumeCode} onChange={(e) => setResumeCode(e.target.value)} />
          <button style={S.btnGhost} disabled={busy || !resumeCode.trim()} onClick={() => {
            localStorage.setItem(CODE_KEY, resumeCode.trim());
            setCode(resumeCode.trim());
          }}>
            Resume
          </button>
        </div>
        <PersistentDisclaimer />
      </div>
    );
  }

  if (inceptionNeeded) {
    return (
      <div style={S.page}>
        <h1 style={S.h1}>One question before the timeline</h1>
        <p style={{ fontSize: 14, lineHeight: 1.6 }}>
          Which statutory deadlines apply depends on when the policy began. The date is on the
          declarations page of the policy — it can also be obtained by asking the carrier.
        </p>
        <div style={S.card}>
          <label style={S.label}>Policy start date (inception date)</label>
          <InceptionForm onSave={saveInception} busy={busy} />
        </div>
        {error && <div style={S.err}>{error}</div>}
        <PersistentDisclaimer />
      </div>
    );
  }

  return <GuideView
    guide={guide} busy={busy} error={error} code={code}
    onEvent={recordEvent} onArtifact={downloadArtifact}
    onSaveDetails={saveDetails} onRefresh={() => fetchGuide(code)} />;
}

function InceptionForm({ onSave, busy }: { onSave: (v: string | null) => void; busy: boolean }) {
  const [value, setValue] = useState("");
  return (
    <>
      <input style={S.input} type="date" value={value} onChange={(e) => setValue(e.target.value)} />
      <button style={S.btn} disabled={busy || !value} onClick={() => onSave(value)}>
        Save date
      </button>
      <button style={S.btnGhost} disabled={busy} onClick={() => onSave(null)}>
        I don't know the date yet
      </button>
    </>
  );
}

function GuideView(props: {
  guide: GuidePayload | null; busy: boolean; error: string | null; code: string;
  onEvent: (name: string) => void; onArtifact: (id: string) => void;
  onSaveDetails: (d: Record<string, string>) => void; onRefresh: () => void;
}) {
  const { guide, busy, error, code, onEvent, onArtifact, onSaveDetails, onRefresh } = props;
  const [copied, setCopied] = useState(false);

  if (!guide) {
    return (
      <div style={S.page}>
        <h1 style={S.h1}>Claim Guide</h1>
        {error && <div style={S.err}>{error}</div>}
        {busy && <p style={S.sub}>Loading your claim…</p>}
        <PersistentDisclaimer />
      </div>
    );
  }

  const st = guide.state;
  const pct = st.phase_count > 0
    ? Math.round((((st.current_sequence ?? -1) + 1) / st.phase_count) * 100)
    : 0;
  const activePhases = guide.phases.filter((p) => st.active_phase_ids.includes(p.phase_id));
  const activeFlags = new Set(guide.red_flags.map((f) => f.name));
  const regime = guide.claim_regime.regime;

  return (
    <div style={S.page}>
      <Link to="/property-casualty" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>
        ← Property &amp; Casualty
      </Link>
      <h1 style={S.h1}>Your claim guide</h1>
      <p style={S.sub}>
        {PERILS[guide.peril] || guide.peril}
        {st.day_number !== null && ` · Day ${st.day_number}`}
        {st.phase_count > 0 && ` · Phase ${(st.current_sequence ?? -1) + 1} of ${st.phase_count}`}
      </p>
      {st.phase_count > 0 && (
        <div style={S.progressTrack}>
          <div style={S.progressFill(pct)} />
        </div>
      )}

      <div style={{ ...S.card, background: "#F0F4FF" }}>
        <div style={{ fontSize: 12, color: "var(--muted)" }}>Your claim code — write it down. Anyone with it can open this claim.</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4, flexWrap: "wrap" }}>
          <span style={{ fontFamily: "var(--mono-font, monospace)", fontSize: 16, fontWeight: 600 }}>{code}</span>
          <button style={{ ...S.btnGhost, width: "auto", minHeight: 40, margin: 0, padding: "0 12px" }}
            onClick={() => {
              navigator.clipboard?.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      {error && <div style={S.err}>{error}</div>}

      {regime === "unknown" && (
        <div style={S.warn}>
          The policy start date is unknown, so the statutory deadlines are not shown.
          {guide.claim_regime.guidance ? ` ${guide.claim_regime.guidance}` : ""}
          <div style={{ marginTop: 8 }}>
            <button style={{ ...S.btnGhost, marginBottom: 0 }} onClick={onRefresh}>Recheck</button>
          </div>
        </div>
      )}

      <DeadlinesPanel deadlines={guide.deadlines} dueThisWeek={guide.due_this_week} />

      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "16px 0 8px" }}>
        Where you are
      </h2>
      {activePhases.length === 0 && (
        <div style={S.card}>
          <p style={{ margin: 0, fontSize: 14 }}>
            Every phase in the guide is complete or not yet started. If the claim is still open,
            record what happened next below.
          </p>
        </div>
      )}
      {activePhases.map((phase) => <PhaseCard key={phase.phase_id} phase={phase} active />)}

      {guide.phases.filter((p) => p.status === "upcoming").length > 0 && (
        <>
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 500, margin: "16px 0 8px" }}>
            Coming up
          </h2>
          {guide.phases.filter((p) => p.status === "upcoming").map((phase) => (
            <details key={phase.phase_id} style={{ ...S.card, marginBottom: 8 }}>
              <summary style={{ fontSize: 14, fontWeight: 500, cursor: "pointer", minHeight: TOUCH_MIN, display: "flex", alignItems: "center" }}>
                {phase.title}
              </summary>
              <p style={{ fontSize: 14, lineHeight: 1.6, margin: "8px 0 0" }}>{phase.plain_summary}</p>
            </details>
          ))}
        </>
      )}

      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "16px 0 8px" }}>
        Record what happened
      </h2>
      <div style={S.card}>
        {Object.entries(EVENT_LABELS).map(([trigger, label]) => (
          <button key={trigger} style={{ ...S.btnGhost, marginBottom: 8 }}
            disabled={busy} onClick={() => onEvent(trigger)}>
            {label}
          </button>
        ))}
        <div style={{ fontSize: 12, color: "var(--muted)" }}>
          Every entry is timestamped in your claim log and moves the timeline.
        </div>
      </div>

      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "16px 0 8px" }}>
        Signals worth watching
      </h2>
      <div style={S.card}>
        <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 8px" }}>
          Check anything that has happened. Two or more active signals together raise an
          escalation notice recommending independent review of the file.
        </p>
        {guide.red_flag_catalog.map((flag) => (
          <div key={flag.name} style={S.listItem}>
            <div style={S.checkBox} onClick={() => !activeFlags.has(flag.name) && onEvent(flag.name)}>
              {activeFlags.has(flag.name) ? "✓" : ""}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14 }}>{flag.label}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{flag.description}</div>
            </div>
          </div>
        ))}
        {guide.escalation && (
          <div style={{ ...S.warn, borderColor: "#C62828", background: "#FFEBEE", marginTop: 12 }}>
            <strong>{guide.escalation.banner}</strong>
            <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13 }}>
              {guide.escalation.resource_links.map((l) => (
                <li key={l.url}><Link to={l.url} style={{ color: "var(--accent)" }}>{l.label}</Link></li>
              ))}
            </ul>
            {guide.escalation.show_financial_screen && guide.escalation.financial_screen_text && (
              <p style={{ marginTop: 10, fontSize: 13, lineHeight: 1.6, borderTop: "1px solid #C62828", paddingTop: 8 }}>
                {guide.escalation.financial_screen_text}
              </p>
            )}
          </div>
        )}
      </div>

      <DetailsPanel details={guide.details} onSave={onSaveDetails} />
      <ArtifactsPanel onArtifact={onArtifact} details={guide.details} />
      <TapsPanel code={code} />

      <PersistentDisclaimer />
    </div>
  );
}

function DetailsPanel({ details, onSave }: {
  details: Record<string, string>; onSave: (d: Record<string, string>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ ...details });
  if (!open) {
    return (
      <div style={S.card}>
        <button style={{ ...S.btnGhost, marginBottom: 0 }} onClick={() => setOpen(true)}>
          Claim details ({DETAIL_FIELDS.filter((f) => details[f.key]).length}/{DETAIL_FIELDS.length} filled)
        </button>
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "8px 0 0" }}>
          These facts prefill the letters and documents this guide generates. Nothing here is
          inferred from uploads — only what you type.
        </p>
      </div>
    );
  }
  return (
    <div style={S.card}>
      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "0 0 8px" }}>
        Claim details
      </h2>
      {DETAIL_FIELDS.map((f) => (
        <div key={f.key}>
          <label style={S.label}>{f.label}</label>
          <input style={S.input} value={form[f.key] || ""}
            onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
        </div>
      ))}
      <button style={S.btn} onClick={() => onSave(form)}>Save details</button>
    </div>
  );
}

function ArtifactsPanel({ onArtifact, details }: {
  onArtifact: (id: string) => void; details: Record<string, string>;
}) {
  const [meta, setMeta] = useState<{ artifacts: Record<string, { title: string; phase: string }>; missing_fields: string[] } | null>(null);
  const [code] = useState(() => localStorage.getItem(CODE_KEY));
  const [open, setOpen] = useState(false);

  const load = async () => {
    if (!code) return;
    const r = await fetch(`${BASE}/api/claims/${code}/artifacts`);
    if (r.ok) setMeta(await r.json());
  };

  if (!open) {
    return (
      <div style={S.card}>
        <button style={{ ...S.btnGhost, marginBottom: 0 }} onClick={() => { setOpen(true); load(); }}>
          Documents this guide can build
        </button>
      </div>
    );
  }
  return (
    <div style={S.card}>
      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "0 0 8px" }}>
        Documents
      </h2>
      <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 12px" }}>
        Drafts you review, correct, and send yourself. This guide does not contact anyone on
        your behalf.
      </p>
      {meta?.missing_fields && meta.missing_fields.length > 0 && (
        <div style={S.warn}>
          Fill in claim details to prefill these letters: {meta.missing_fields.join(", ")}.
        </div>
      )}
      {meta && Object.entries(meta.artifacts).map(([id, a]) => (
        <button key={id} style={{ ...S.btnGhost, marginBottom: 8 }}
          onClick={() => onArtifact(id)}>
          {a.title}
        </button>
      ))}
      {!meta && <p style={S.sub}>Loading catalog…</p>}
    </div>
  );
}

function TapsPanel({ code }: { code: string }) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <div style={S.card}>
        <button style={{ ...S.btnGhost, marginBottom: 0 }} onClick={() => setOpen(true)}>
          Get help with a document or term
        </button>
        <p style={{ fontSize: 12, color: "var(--muted)", margin: "8px 0 0" }}>
          Optional, on-demand help. Nothing here computes deadlines, decides coverage, or
          predicts outcomes — by design.
        </p>
      </div>
    );
  }
  return (
    <div style={S.card}>
      <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500, margin: "0 0 8px" }}>
        On-demand help
      </h2>
      <ExplainLetterTap code={code} />
      <DescribeItemTap />
      <NotesToDemandTap />
      <DefineTermTap />
      <ClassifyDocumentTap />
    </div>
  );
}

function useTapPost(url: string) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async (form: FormData) => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${BASE}${url}`, { method: "POST", body: form });
      const data = await r.json().catch(() => null);
      if (!r.ok) {
        setError(data?.detail || `HTTP ${r.status}`);
        return;
      }
      if (data?.error) {
        setError(data.message || "That action is unavailable right now.");
        return;
      }
      setResult(data);
    } catch {
      setError("Could not reach the help service.");
    } finally {
      setBusy(false);
    }
  };
  return { result, busy, error, run };
}

function TapShell({ title, blurb, children, result, error, busy }: {
  title: string; blurb: string; children: React.ReactNode;
  result: Record<string, unknown> | null; error: string | null; busy: boolean;
}) {
  return (
    <details style={{ borderTop: "1px solid var(--border)", paddingTop: 8, marginTop: 8 }}>
      <summary style={{ fontSize: 14, fontWeight: 500, cursor: "pointer", minHeight: TOUCH_MIN, display: "flex", alignItems: "center" }}>
        {title}
      </summary>
      <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 8px" }}>{blurb}</p>
      {children}
      {busy && <p style={S.sub}>Working…</p>}
      {error && <div style={S.err}>{error}</div>}
      {result && (
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "#F5F5F2",
          padding: 10, borderRadius: "var(--radius)" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </details>
  );
}

function ExplainLetterTap({ code }: { code: string }) {
  const { result, busy, error, run } = useTapPost("/api/property-casualty/tap/explain-letter");
  return (
    <TapShell title="Explain a letter I received" busy={busy} error={error} result={result}
      blurb="Upload a letter from the insurer. The explanation quotes deadline language verbatim and never computes dates.">
      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={(e) => {
        const f = e.target.files?.[0];
        if (f) {
          const fd = new FormData();
          fd.append("file", f);
          run(fd);
        }
      }} />
    </TapShell>
  );
}

function DescribeItemTap() {
  const { result, busy, error, run } = useTapPost("/api/property-casualty/tap/describe-item");
  const [notes, setNotes] = useState("");
  return (
    <TapShell title="Turn notes into an inventory row" busy={busy} error={error} result={result}
      blurb="Describe one item; the row goes into your contents inventory.">
      <textarea style={{ ...S.input, minHeight: 80, paddingTop: 10 }} value={notes}
        onChange={(e) => setNotes(e.target.value)} placeholder="Kitchen toaster, Cuisinart, 3 years old, paid $45" />
      <button style={S.btn} disabled={busy || !notes.trim()} onClick={() => {
        const fd = new FormData();
        fd.append("notes", notes);
        run(fd);
      }}>Describe item</button>
    </TapShell>
  );
}

function NotesToDemandTap() {
  const { result, busy, error, run } = useTapPost("/api/property-casualty/tap/notes-to-demand");
  const [notes, setNotes] = useState("");
  return (
    <TapShell title="Turn notes into a demand letter draft" busy={busy} error={error} result={result}
      blurb="A plain, factual draft body. No legal conclusions, no computed dates.">
      <textarea style={{ ...S.input, minHeight: 80, paddingTop: 10 }} value={notes}
        onChange={(e) => setNotes(e.target.value)} placeholder="What the insurer's estimate says vs yours, line by line" />
      <button style={S.btn} disabled={busy || !notes.trim()} onClick={() => {
        const fd = new FormData();
        fd.append("notes", notes);
        run(fd);
      }}>Draft letter</button>
    </TapShell>
  );
}

function DefineTermTap() {
  const { result, busy, error, run } = useTapPost("/api/property-casualty/tap/define-term");
  const [term, setTerm] = useState("");
  return (
    <TapShell title="What does this term mean?" busy={busy} error={error} result={result}
      blurb="Plain-language definitions, with statute citations only when the term's meaning comes from the law.">
      <input style={S.input} value={term} onChange={(e) => setTerm(e.target.value)}
        placeholder="ACV, reservation of rights, EUO…" />
      <button style={S.btn} disabled={busy || !term.trim()} onClick={() => {
        const fd = new FormData();
        fd.append("term", term);
        run(fd);
      }}>Define</button>
    </TapShell>
  );
}

function ClassifyDocumentTap() {
  const { result, busy, error, run } = useTapPost("/api/property-casualty/tap/classify-document");
  return (
    <TapShell title="What kind of document is this?" busy={busy} error={error} result={result}
      blurb="Classifies an uploaded document into a known claim-document type.">
      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={(e) => {
        const f = e.target.files?.[0];
        if (f) {
          const fd = new FormData();
          fd.append("file", f);
          run(fd);
        }
      }} />
    </TapShell>
  );
}
