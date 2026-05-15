import { useState } from "react";
import { useWizard } from "./WizardContext";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

type GenerateResult = {
  forms: { name: string; url: string }[];
  filing_instructions: string;
  filing_fee_usd: number;
  clerk_url: string;
  service_of_process_options: string[];
};

export default function ReviewStep() {
  const { data, back } = useWizard();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/small-claims/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_type: data.claim_type,
          amount: Number(data.amount),
          defendant_type: data.defendant_type,
          defendant_name: data.defendant_name,
          defendant_address: data.defendant_address,
          defendant_phone: data.defendant_phone || null,
          defendant_email: data.defendant_email || null,
          county: data.county,
        }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const j = (await r.json()) as GenerateResult;
      setResult(j);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <section style={{ padding: 32 }}>
        <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
          Your filing packet
        </h2>
        <p style={{ color: "var(--muted)", marginBottom: 16 }}>
          {result.filing_instructions}
        </p>
        <p style={{ marginBottom: 16 }}>
          <strong>Filing fee:</strong> ${result.filing_fee_usd}
        </p>
        <h3 className="mono" style={{ fontSize: 16, margin: "16px 0 8px" }}>
          Forms
        </h3>
        <ul style={{ paddingLeft: 16, marginBottom: 16 }}>
          {result.forms.map((f) => (
            <li key={f.url} style={{ marginBottom: 6 }}>
              <a
                href={f.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--accent)" }}
              >
                {f.name}
              </a>
            </li>
          ))}
        </ul>
        <h3 className="mono" style={{ fontSize: 16, margin: "16px 0 8px" }}>
          Service of process options
        </h3>
        <ul style={{ paddingLeft: 16, marginBottom: 16 }}>
          {result.service_of_process_options.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <p>
          <a
            href={result.clerk_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn"
            style={{ textDecoration: "none" }}
          >
            OPEN CLERK PORTAL →
          </a>
        </p>
      </section>
    );
  }

  return (
    <section style={{ padding: 32 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
        Review your claim
      </h2>
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "180px 1fr",
          rowGap: 8,
          columnGap: 16,
          margin: 0,
        }}
      >
        <dt className="mono" style={{ color: "var(--muted)" }}>Claim type</dt>
        <dd>{data.claim_type}</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>Amount</dt>
        <dd>${data.amount}</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>Defendant</dt>
        <dd>
          {data.defendant_name} ({data.defendant_type})<br />
          {data.defendant_address}
          {data.defendant_phone && (
            <>
              <br />
              {data.defendant_phone}
            </>
          )}
          {data.defendant_email && (
            <>
              <br />
              {data.defendant_email}
            </>
          )}
        </dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>County</dt>
        <dd>{data.county}</dd>
      </dl>

      {error && (
        <p
          role="alert"
          style={{
            color: "var(--danger)",
            border: "1px solid var(--danger)",
            padding: 12,
            marginTop: 16,
          }}
        >
          {error}
        </p>
      )}

      <div
        style={{
          marginTop: 24,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <button className="btn" onClick={back} disabled={loading}>
          ← BACK
        </button>
        <button className="btn" onClick={generate} disabled={loading}>
          {loading ? "GENERATING…" : "GENERATE MY FORM PACKET"}
        </button>
      </div>
    </section>
  );
}
