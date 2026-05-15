import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../packet/LanguageToggle";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

const ISSUE_TYPES = ["Heat", "AC", "Water", "Mold", "Electrical", "Structural", "Other"];
const INTENTS = ["Withhold rent", "Terminate lease", "Repair-and-deduct"];

// Phase 23 — /api/landlord/repairs/generate returns packet_id + checkout.
type GenerateResult = {
  packet_id: string;
  fee_usd: number;
  file_count: number;
  checkout_url: string;
};

export default function RepairsFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    property_address: "",
    issue_type: "",
    issue_description: "",
    prior_communication: "",
    tenant_intent: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(() => readLanguage());

  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const step1Valid =
    form.property_address && form.issue_type && form.issue_description;
  const step2Valid = form.prior_communication.trim().length > 0;
  const step3Valid = form.tenant_intent.length > 0;

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/landlord/repairs/generate`, {
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
            Step 1 — The issue
          </h2>
          <label>
            <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
              Property address *
            </span>
            <textarea
              className="input"
              value={form.property_address}
              onChange={(e) => set("property_address", e.target.value)}
              style={{ width: "100%", minHeight: 60 }}
            />
          </label>
          <fieldset style={{ border: 0, padding: 0 }}>
            <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
              Issue type *
            </legend>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8 }}>
              {ISSUE_TYPES.map((t) => (
                <label
                  key={t}
                  style={{
                    border: "1px solid var(--border)",
                    padding: 8,
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    checked={form.issue_type === t}
                    onChange={() => set("issue_type", t)}
                  />
                  <span>{t}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
              Issue description *
            </span>
            <textarea
              className="input"
              value={form.issue_description}
              onChange={(e) => set("issue_description", e.target.value)}
              style={{ width: "100%", minHeight: 80 }}
            />
          </label>
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
            Step 2 — Prior communication
          </h2>
          <label>
            <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
              When and how have you contacted the landlord? *
            </span>
            <textarea
              className="input"
              value={form.prior_communication}
              onChange={(e) => set("prior_communication", e.target.value)}
              style={{ width: "100%", minHeight: 100 }}
              placeholder="e.g. Email March 1 (no reply); phone call March 5 (told to wait)…"
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
            Step 3 — Your intent
          </h2>
          <fieldset style={{ border: 0, padding: 0 }}>
            <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
              What do you intend to do if landlord doesn't cure?
            </legend>
            <div style={{ display: "grid", gap: 8 }}>
              {INTENTS.map((t) => (
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
                    checked={form.tenant_intent === t}
                    onChange={() => set("tenant_intent", t)}
                  />
                  <span>{t}</span>
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
              {submitting ? "GENERATING…" : "GENERATE 7-DAY NOTICE"}
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
