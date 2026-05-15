import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../packet/LanguageToggle";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

const EVICTION_TYPES = ["Nonpayment", "Nonrenewal", "Cause"];
const NOTICE_TYPES = ["3-day", "7-day", "15-day"];
const DEFENSES = [
  "Paid rent",
  "Retaliation",
  "Withholding for repairs",
  "Improper notice",
  "Other",
];

// Phase 23 — /api/landlord/eviction/generate returns packet_id + checkout.
type GenerateResult = {
  packet_id: string;
  fee_usd: number;
  file_count: number;
  checkout_url: string;
};

export default function EvictionFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    eviction_type: "",
    notice_type: "",
    notice_date: "",
    defenses: [] as string[],
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(() => readLanguage());

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const toggleDefense = (d: string) =>
    setForm((f) => ({
      ...f,
      defenses: f.defenses.includes(d)
        ? f.defenses.filter((x) => x !== d)
        : [...f.defenses, d],
    }));

  const step1Valid = form.eviction_type.length > 0;
  const step2Valid = form.notice_type.length > 0 && form.notice_date.length > 0;
  const step3Valid = form.defenses.length > 0;

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/landlord/eviction/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, language }),
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
      setSubmitting(false);
    }
  }

  return (
    <section style={{ padding: 32 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 8,
        }}
      >
        <LanguageToggle value={language} onChange={setLanguage} />
      </div>
      <ProgressBar step={step} />

      {step === 1 && (
        <div style={{ display: "grid", gap: 16 }}>
          <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
            Step 1 — Type of eviction
          </h2>
          <fieldset style={{ border: 0, padding: 0 }}>
            <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
              What kind of eviction are you facing? *
            </legend>
            <div style={{ display: "grid", gap: 8 }}>
              {EVICTION_TYPES.map((t) => (
                <label
                  key={t}
                  style={{
                    border: "1px solid var(--border)",
                    padding: 12,
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    checked={form.eviction_type === t}
                    onChange={() => set("eviction_type", t)}
                  />
                  <span>{t}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <NavRow
            onNext={() => setStep(2)}
            nextDisabled={!step1Valid}
            showBack={false}
          />
        </div>
      )}

      {step === 2 && (
        <div style={{ display: "grid", gap: 16 }}>
          <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
            Step 2 — Notice received
          </h2>
          <fieldset style={{ border: 0, padding: 0 }}>
            <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
              What type of notice did you receive? *
            </legend>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap: 8,
              }}
            >
              {NOTICE_TYPES.map((t) => (
                <label
                  key={t}
                  style={{
                    border: "1px solid var(--border)",
                    padding: 12,
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    checked={form.notice_type === t}
                    onChange={() => set("notice_type", t)}
                  />
                  <span>{t}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            <span
              style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}
            >
              Date the notice was received *
            </span>
            <input
              className="input"
              type="date"
              value={form.notice_date}
              onChange={(e) => set("notice_date", e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <NavRow
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
            nextDisabled={!step2Valid}
          />
        </div>
      )}

      {step === 3 && (
        <div style={{ display: "grid", gap: 16 }}>
          <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
            Step 3 — Defenses
          </h2>
          <fieldset style={{ border: 0, padding: 0 }}>
            <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
              Which defenses apply? (pick all that apply)
            </legend>
            <div style={{ display: "grid", gap: 8 }}>
              {DEFENSES.map((d) => (
                <label
                  key={d}
                  style={{
                    border: "1px solid var(--border)",
                    padding: 12,
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={form.defenses.includes(d)}
                    onChange={() => toggleDefense(d)}
                  />
                  <span>{d}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && (
            <p
              role="alert"
              style={{
                color: "var(--danger)",
                border: "1px solid var(--danger)",
                padding: 12,
              }}
            >
              {error}
            </p>
          )}
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button
              className="btn"
              onClick={() => setStep(2)}
              disabled={submitting}
            >
              ← BACK
            </button>
            <button
              className="btn"
              onClick={submit}
              disabled={!step3Valid || submitting}
              style={{ opacity: !step3Valid || submitting ? 0.4 : 1 }}
            >
              {submitting ? "GENERATING…" : "GENERATE ANSWER"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function NavRow({
  onBack,
  onNext,
  nextDisabled,
  showBack = true,
}: {
  onBack?: () => void;
  onNext: () => void;
  nextDisabled: boolean;
  showBack?: boolean;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      {showBack ? (
        <button className="btn" onClick={onBack}>
          ← BACK
        </button>
      ) : (
        <span />
      )}
      <button
        className="btn"
        onClick={onNext}
        disabled={nextDisabled}
        style={{ opacity: nextDisabled ? 0.4 : 1 }}
      >
        NEXT →
      </button>
    </div>
  );
}

function ProgressBar({ step }: { step: number }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <p
        className="mono"
        style={{ margin: "0 0 8px", fontSize: 12, letterSpacing: "0.08em" }}
      >
        STEP {step} OF 3
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 4,
        }}
      >
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            style={{
              height: 4,
              background: i <= step ? "var(--accent)" : "var(--border-strong)",
            }}
          />
        ))}
      </div>
    </div>
  );
}

// Phase 23 — ResultCard removed; navigation to /filing-packet/:packetId
// after submit replaces the inline result display.
