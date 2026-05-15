import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../packet/LanguageToggle";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

export type EligibilityResult = {
  status: "eligible" | "likely_eligible" | "not_eligible";
  reason: string;
  applicable_statute: string;
  next_steps: string[];
};

// Phase 23 — /api/expungement/generate now returns a packet_id + Stripe
// checkout URL instead of the prior scaffold JSON.
export type GenerateResult = {
  packet_id: string;
  fee_usd: number;
  file_count: number;
  checkout_url: string;
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
  const navigate = useNavigate();
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(() => readLanguage());

  async function generatePacket() {
    setGenerating(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/expungement/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...quizPayload, language }),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      const j = (await r.json()) as GenerateResult;
      try {
        sessionStorage.setItem(
          `lc.packet.${j.packet_id}.checkout_url`,
          j.checkout_url
        );
      } catch {
        /* non-fatal */
      }
      navigate(`/filing-packet/${j.packet_id}`);
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2
          className="mono"
          style={{ fontSize: 22, margin: 0, color: cfg.border }}
        >
          {cfg.heading}
        </h2>
        {cfg.canGenerate && (
          <LanguageToggle value={language} onChange={setLanguage} />
        )}
      </div>
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

      {cfg.canGenerate && (
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
