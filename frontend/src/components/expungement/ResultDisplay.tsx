import { useState } from "react";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

export type EligibilityResult = {
  status: "eligible" | "likely_eligible" | "not_eligible";
  reason: string;
  applicable_statute: string;
  next_steps: string[];
};

export type GenerateResult = {
  forms: { name: string; url: string }[];
  filing_instructions: string;
  estimated_timeline_months: number;
};

type Props = {
  result: EligibilityResult;
  quizPayload: Record<string, string>;
  onRestart: () => void;
};

const STATUS_CONFIG = {
  eligible: {
    border: "var(--success)",
    heading: "YOU APPEAR ELIGIBLE",
    canGenerate: true,
  },
  likely_eligible: {
    border: "var(--accent)",
    heading: "YOU MAY BE ELIGIBLE FOR SEALING",
    canGenerate: true,
  },
  not_eligible: {
    border: "var(--danger)",
    heading: "YOU DO NOT APPEAR ELIGIBLE",
    canGenerate: false,
  },
} as const;

export default function ResultDisplay({ result, quizPayload, onRestart }: Props) {
  const cfg = STATUS_CONFIG[result.status];
  const [packet, setPacket] = useState<GenerateResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generatePacket() {
    setGenerating(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/expungement/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(quizPayload),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setPacket((await r.json()) as GenerateResult);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <section
      style={{
        padding: 32,
        border: `2px solid ${cfg.border}`,
        margin: 32,
      }}
    >
      <h2
        className="mono"
        style={{ fontSize: 22, margin: "0 0 16px", color: cfg.border }}
      >
        {cfg.heading}
      </h2>
      <p style={{ marginBottom: 12 }}>{result.reason}</p>
      <p style={{ color: "var(--muted)", fontSize: 14, marginBottom: 16 }}>
        Applicable statute: <span className="mono">{result.applicable_statute}</span>
      </p>

      <h3 className="mono" style={{ fontSize: 16, margin: "16px 0 8px" }}>
        Next steps
      </h3>
      <ul style={{ paddingLeft: 16, marginBottom: 16 }}>
        {result.next_steps.map((s) => (
          <li key={s} style={{ marginBottom: 6 }}>
            {s}
          </li>
        ))}
      </ul>

      {!cfg.canGenerate && (
        <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 8 }}>
          Consult a licensed FL attorney for case-specific advice.
        </p>
      )}

      {cfg.canGenerate && !packet && (
        <button
          className="btn"
          onClick={generatePacket}
          disabled={generating}
          style={{ marginTop: 8 }}
        >
          {generating ? "GENERATING…" : "GENERATE MY EXPUNGEMENT PACKET"}
        </button>
      )}

      {error && (
        <p
          role="alert"
          style={{
            color: "var(--danger)",
            border: "1px solid var(--danger)",
            padding: 12,
            marginTop: 12,
          }}
        >
          {error}
        </p>
      )}

      {packet && (
        <div style={{ marginTop: 24 }}>
          <h3 className="mono" style={{ fontSize: 16, margin: "0 0 8px" }}>
            Your expungement packet
          </h3>
          <p style={{ color: "var(--muted)", marginBottom: 12 }}>
            {packet.filing_instructions}
          </p>
          <p style={{ marginBottom: 12 }}>
            <strong>Estimated timeline:</strong>{" "}
            {packet.estimated_timeline_months} months
          </p>
          <ul style={{ paddingLeft: 16 }}>
            {packet.forms.map((f) => (
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
        </div>
      )}

      <p style={{ marginTop: 24 }}>
        <button
          className="btn"
          onClick={onRestart}
          style={{ background: "transparent" }}
        >
          START OVER
        </button>
      </p>
    </section>
  );
}
