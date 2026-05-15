import { useState } from "react";
import counties from "../../data/fl_counties.json";
import type { ContestResult, County, TrafficForm } from "./types";

const COUNTIES = counties as County[];
const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";
const FLHSMV_SCHOOL_URL =
  "https://www.flhsmv.gov/driver-licenses-id-cards/locations/";

type Props = {
  form: TrafficForm;
  onBack: () => void;
};

export default function GenerateStep({ form, onBack }: Props) {
  const county = COUNTIES.find((c) => c.name === form.county);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ContestResult | null>(null);

  async function submitContest() {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/traffic/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          citation_type: form.citation_type,
          citation_number: form.citation_number,
          issue_date: form.issue_date,
          county: form.county,
          chosen_path: form.chosen_path,
        }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setResult((await r.json()) as ContestResult);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section style={{ padding: 32, display: "grid", gap: 16 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
        Step 3 — Next steps
      </h2>

      <SummaryCard form={form} />

      {form.chosen_path === "pay" && (
        <PayPath county={county} />
      )}

      {form.chosen_path === "school" && (
        <SchoolPath />
      )}

      {form.chosen_path === "contest" && !result && (
        <ContestPath
          onSubmit={submitContest}
          submitting={submitting}
          error={error}
        />
      )}

      {form.chosen_path === "contest" && result && (
        <ContestResultCard r={result} />
      )}

      <div style={{ display: "flex", justifyContent: "flex-start" }}>
        <button className="btn" onClick={onBack} disabled={submitting}>
          ← BACK
        </button>
      </div>
    </section>
  );
}

function SummaryCard({ form }: { form: TrafficForm }) {
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        padding: 12,
        fontSize: 13,
        display: "grid",
        gap: 4,
      }}
    >
      <div>
        <span className="mono" style={{ color: "var(--muted)" }}>TYPE:</span>{" "}
        {form.citation_type}
      </div>
      <div>
        <span className="mono" style={{ color: "var(--muted)" }}>CITATION:</span>{" "}
        {form.citation_number}
      </div>
      <div>
        <span className="mono" style={{ color: "var(--muted)" }}>COUNTY:</span>{" "}
        {form.county}
      </div>
      <div>
        <span className="mono" style={{ color: "var(--muted)" }}>PATH:</span>{" "}
        {form.chosen_path.toUpperCase()}
      </div>
    </div>
  );
}

function PayPath({ county }: { county: County | undefined }) {
  return (
    <article
      style={{
        border: "2px solid var(--success)",
        padding: 16,
        display: "grid",
        gap: 8,
      }}
    >
      <h3 className="mono" style={{ fontSize: 16, margin: 0 }}>
        PAY THE CITATION
      </h3>
      <p style={{ margin: 0 }}>
        Pay directly through the county clerk. Payment admits responsibility
        and points (if any) apply to your driving record.
      </p>
      {county ? (
        <a
          href={county.clerk_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn"
          style={{ justifySelf: "start", textDecoration: "none" }}
        >
          OPEN {county.name.toUpperCase()} CLERK PORTAL →
        </a>
      ) : (
        <p style={{ color: "var(--muted)" }}>County not selected.</p>
      )}
    </article>
  );
}

function SchoolPath() {
  return (
    <article
      style={{
        border: "2px solid var(--success)",
        padding: 16,
        display: "grid",
        gap: 8,
      }}
    >
      <h3 className="mono" style={{ fontSize: 16, margin: 0 }}>
        ELECT TRAFFIC SCHOOL
      </h3>
      <p style={{ margin: 0 }}>
        File an election to attend a state-approved Basic Driver Improvement
        (BDI) course. On completion, the citation is withheld from your
        driving record (no points). You may only elect BDI once every 12
        months and up to 5 times in your lifetime.
      </p>
      <a
        href={FLHSMV_SCHOOL_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="btn"
        style={{ justifySelf: "start", textDecoration: "none" }}
      >
        FIND AN APPROVED SCHOOL (FLHSMV) →
      </a>
    </article>
  );
}

function ContestPath({
  onSubmit,
  submitting,
  error,
}: {
  onSubmit: () => void;
  submitting: boolean;
  error: string | null;
}) {
  return (
    <article
      style={{
        border: "1px solid var(--border)",
        padding: 16,
        display: "grid",
        gap: 8,
      }}
    >
      <h3 className="mono" style={{ fontSize: 16, margin: 0 }}>
        CONTEST THE CITATION
      </h3>
      <p style={{ margin: 0 }}>
        You'll request a court hearing. The filing deadline is short — usually
        30 days from the issue date. Generate a hearing request letter and
        preparation checklist below.
      </p>
      {error && (
        <p
          role="alert"
          style={{
            color: "var(--danger)",
            border: "1px solid var(--danger)",
            padding: 12,
            margin: 0,
          }}
        >
          {error}
        </p>
      )}
      <button
        className="btn"
        onClick={onSubmit}
        disabled={submitting}
        style={{ justifySelf: "start" }}
      >
        {submitting ? "GENERATING…" : "GENERATE HEARING REQUEST"}
      </button>
    </article>
  );
}

function ContestResultCard({ r }: { r: ContestResult }) {
  return (
    <article
      style={{
        border: "2px solid var(--success)",
        padding: 16,
        display: "grid",
        gap: 8,
      }}
    >
      <h3 className="mono" style={{ fontSize: 16, margin: 0 }}>
        {r.document_name}
      </h3>
      <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
        File at: <span className="mono">{r.filing_location}</span>
      </p>
      <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
        Filing deadline:{" "}
        <span className="mono">{r.filing_deadline_days} days from issue</span>
      </p>
      <h4 className="mono" style={{ fontSize: 14, margin: "8px 0 0" }}>
        Preparation tips
      </h4>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        {r.hearing_preparation_tips.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
    </article>
  );
}
