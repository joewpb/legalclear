import { useRef, useState } from "react";

type Props = {
  onAnalyze: (primary: File, supplementary: File[]) => void;
  submitting: boolean;
  error: string | null;
};

const MAX_SUPPLEMENTARY = 4;
const ACCEPT = ".pdf,application/pdf,image/*,.txt";

export default function UploadInterface({
  onAnalyze,
  submitting,
  error,
}: Props) {
  const [primary, setPrimary] = useState<File | null>(null);
  const [supplementary, setSupplementary] = useState<File[]>([]);
  const supplementaryRef = useRef<HTMLInputElement>(null);

  function pickSupplementary(files: FileList | null) {
    if (!files) return;
    const arr = Array.from(files);
    const merged = [...supplementary, ...arr].slice(0, MAX_SUPPLEMENTARY);
    setSupplementary(merged);
    if (supplementaryRef.current) supplementaryRef.current.value = "";
  }

  function removeSupplementary(i: number) {
    setSupplementary((s) => s.filter((_, idx) => idx !== i));
  }

  const ready = primary !== null && !submitting;

  return (
    <section style={{ padding: 32, display: "grid", gap: 16 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
        Upload documents
      </h2>

      <label
        style={{
          border: "2px dashed var(--border-strong)",
          padding: 24,
          display: "grid",
          gap: 8,
          cursor: "pointer",
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 13, letterSpacing: "0.08em" }}
        >
          STEP 1 — POLICE REPORT (REQUIRED)
        </span>
        <span style={{ color: "var(--muted)", fontSize: 13 }}>
          {primary ? primary.name : "Click to choose a PDF"}
        </span>
        <input
          type="file"
          accept={ACCEPT}
          onChange={(e) => setPrimary(e.target.files?.[0] ?? null)}
          style={{ display: "none" }}
        />
      </label>

      <label
        style={{
          border: "2px dashed var(--border)",
          padding: 24,
          display: "grid",
          gap: 8,
          cursor: "pointer",
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 13, letterSpacing: "0.08em" }}
        >
          STEP 2 — SUPPLEMENTARY (OPTIONAL, UP TO {MAX_SUPPLEMENTARY})
        </span>
        <span style={{ color: "var(--muted)", fontSize: 13 }}>
          Witness statements, body cam transcripts, dispatch logs
        </span>
        <input
          ref={supplementaryRef}
          type="file"
          accept={ACCEPT}
          multiple
          onChange={(e) => pickSupplementary(e.target.files)}
          style={{ display: "none" }}
        />
      </label>

      {supplementary.length > 0 && (
        <ul style={{ display: "grid", gap: 8, padding: 0, listStyle: "none" }}>
          {supplementary.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              style={{
                border: "1px solid var(--border)",
                padding: "8px 12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
              }}
            >
              <span style={{ fontSize: 13 }}>{f.name}</span>
              <button
                type="button"
                className="btn"
                onClick={() => removeSupplementary(i)}
                style={{ padding: "4px 8px", fontSize: 11 }}
              >
                REMOVE
              </button>
            </li>
          ))}
        </ul>
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

      <button
        className="btn"
        onClick={() => primary && onAnalyze(primary, supplementary)}
        disabled={!ready}
        style={{
          opacity: ready ? 1 : 0.4,
          justifySelf: "start",
          padding: "12px 24px",
        }}
      >
        {submitting ? "ANALYZING… (15–45s)" : "ANALYZE"}
      </button>

      {submitting && (
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          The scanner is reviewing the documents for procedural and factual
          discrepancies. This can take 15–45 seconds.
        </p>
      )}
    </section>
  );
}
