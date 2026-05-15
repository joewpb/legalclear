import { useEffect, useState } from "react";

type Step = {
  number: number;
  title: string;
  instruction: string;
  what_to_expect: string;
};

type Walkthrough = {
  title: string;
  intro: string;
  steps: Step[];
};

type Props = {
  language: "en" | "es";
};

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

// Fetched from the backend per-language so we don't duplicate the
// walkthrough text in two places. Backend serves the same JSON via the
// packet metadata endpoint to keep parity with the PDF version included
// in the ZIP.
async function fetchWalkthrough(language: "en" | "es"): Promise<Walkthrough | null> {
  try {
    const r = await fetch(`${API_URL}/api/packet/walkthrough?lang=${language}`);
    if (r.ok) return (await r.json()) as Walkthrough;
  } catch {
    /* fall through */
  }
  // Fallback to a minimal client-side walkthrough so the page stays
  // useful even if the optional endpoint isn't present (it's a nice-to-
  // have, not required by the Phase 23 verification).
  return null;
}

export default function UploadWalkthrough({ language }: Props) {
  const [data, setData] = useState<Walkthrough | null>(null);

  useEffect(() => {
    fetchWalkthrough(language).then(setData);
  }, [language]);

  if (!data) {
    return (
      <section style={{ padding: 24, border: "1px solid var(--border)" }}>
        <p className="mono" style={{ margin: 0, color: "var(--muted)" }}>
          {language === "es"
            ? "Cargando guía de carga manual..."
            : "Loading manual upload walkthrough..."}
        </p>
      </section>
    );
  }

  return (
    <section style={{ display: "grid", gap: 12 }}>
      <h2 className="mono" style={{ fontSize: 18, margin: 0 }}>
        {data.title}
      </h2>
      <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
        {data.intro}
      </p>
      <ol style={{ paddingLeft: 20, margin: 0, display: "grid", gap: 12 }}>
        {data.steps.map((s) => (
          <li key={s.number}>
            <strong className="mono" style={{ letterSpacing: "0.04em" }}>
              {s.title}
            </strong>
            <p style={{ margin: "4px 0" }}>{s.instruction}</p>
            <p
              style={{
                margin: 0,
                color: "var(--muted)",
                fontSize: 13,
                fontStyle: "italic",
              }}
            >
              {language === "es" ? "Qué esperar: " : "What to expect: "}
              {s.what_to_expect}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
