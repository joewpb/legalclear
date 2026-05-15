import { useState } from "react";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

type Props = {
  packetId: string;
  language: "en" | "es";
  initialConfirmation?: string | null;
  initialFiledAt?: string | null;
};

const COPY = {
  en: {
    heading: "Track your filing",
    body:
      "After you submit on the e-filing portal, paste the clerk's confirmation number here so LegalClear can record the filing date.",
    placeholder: "Confirmation number (e.g. MDC-2026-12345)",
    submit: "RECORD CONFIRMATION",
    submitting: "RECORDING…",
    success: "Tracked. Filed on",
    error: "Failed to record. Try again.",
  },
  es: {
    heading: "Dar seguimiento a su presentación",
    body:
      "Después de presentar en el portal electrónico, pegue aquí el número de confirmación del secretario para que LegalClear registre la fecha de presentación.",
    placeholder: "Número de confirmación (ej. MDC-2026-12345)",
    submit: "REGISTRAR CONFIRMACIÓN",
    submitting: "REGISTRANDO…",
    success: "Registrado. Presentado el",
    error: "No se pudo registrar. Intente nuevamente.",
  },
};

export default function FilingTracker({
  packetId,
  language,
  initialConfirmation,
  initialFiledAt,
}: Props) {
  const t = COPY[language];
  const [num, setNum] = useState(initialConfirmation ?? "");
  const [confirmation, setConfirmation] = useState<string | null>(
    initialConfirmation ?? null
  );
  const [filedAt, setFiledAt] = useState<string | null>(
    initialFiledAt ?? null
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!num.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(
        `${API_URL}/api/packet/${packetId}/track?confirmation_number=${encodeURIComponent(num.trim())}`,
        { method: "POST" }
      );
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setConfirmation(num.trim());
      setFiledAt(new Date().toISOString());
    } catch (e) {
      setError((e as Error).message || t.error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      style={{
        border: "1px solid var(--border)",
        padding: 24,
        display: "grid",
        gap: 12,
      }}
    >
      <h2 className="mono" style={{ fontSize: 18, margin: 0 }}>
        {t.heading}
      </h2>
      <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>{t.body}</p>

      {confirmation ? (
        <p
          className="mono"
          style={{
            margin: 0,
            color: "var(--success)",
            letterSpacing: "0.04em",
          }}
        >
          {t.success}{" "}
          <span style={{ color: "var(--text)" }}>
            {filedAt ? new Date(filedAt).toLocaleString() : "now"}
          </span>{" "}
          — {confirmation}
        </p>
      ) : (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            className="input"
            value={num}
            onChange={(e) => setNum(e.target.value)}
            placeholder={t.placeholder}
            style={{ flex: 1, minWidth: 240 }}
          />
          <button
            className="btn"
            onClick={submit}
            disabled={submitting || !num.trim()}
          >
            {submitting ? t.submitting : t.submit}
          </button>
        </div>
      )}

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
    </section>
  );
}
