import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../packet/LanguageToggle";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

// Phase 23 — /api/landlord/deposit/generate returns a packet_id + Stripe
// checkout URL. Navigate to /filing-packet/:packetId after generation.
type GenerateResult = {
  packet_id: string;
  fee_usd: number;
  file_count: number;
  checkout_url: string;
};

export default function DepositFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    move_out_date: "",
    deposit_amount: "",
    current_address: "",
    landlord_name: "",
    landlord_address: "",
    reason_given: "",
    tenant_response: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(() => readLanguage());

  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const step1Valid =
    form.move_out_date && form.deposit_amount && form.current_address;
  const step2Valid = form.landlord_name && form.landlord_address;

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/landlord/deposit/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          move_out_date: form.move_out_date,
          deposit_amount: Number(form.deposit_amount),
          current_address: form.current_address,
          landlord_name: form.landlord_name,
          landlord_address: form.landlord_address,
          reason_given: form.reason_given || null,
          tenant_response: form.tenant_response || null,
          language,
        }),
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
            Step 1 — Your move-out
          </h2>
          <Field label="Move-out date *">
            <input
              className="input"
              type="date"
              value={form.move_out_date}
              onChange={(e) => set("move_out_date", e.target.value)}
              style={{ width: "100%" }}
            />
          </Field>
          <Field label="Deposit amount (USD) *">
            <input
              className="input"
              type="number"
              min={0}
              step="0.01"
              value={form.deposit_amount}
              onChange={(e) => set("deposit_amount", e.target.value)}
              style={{ width: "100%" }}
            />
          </Field>
          <Field label="Current forwarding address *">
            <textarea
              className="input"
              value={form.current_address}
              onChange={(e) => set("current_address", e.target.value)}
              style={{ width: "100%", minHeight: 72 }}
            />
          </Field>
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
            Step 2 — Landlord
          </h2>
          <Field label="Landlord name *">
            <input
              className="input"
              value={form.landlord_name}
              onChange={(e) => set("landlord_name", e.target.value)}
              style={{ width: "100%" }}
            />
          </Field>
          <Field label="Landlord address *">
            <textarea
              className="input"
              value={form.landlord_address}
              onChange={(e) => set("landlord_address", e.target.value)}
              style={{ width: "100%", minHeight: 72 }}
            />
          </Field>
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
            Step 3 — Reason given + your response
          </h2>
          <Field label="Reason landlord gave (if any)">
            <textarea
              className="input"
              value={form.reason_given}
              onChange={(e) => set("reason_given", e.target.value)}
              style={{ width: "100%", minHeight: 60 }}
            />
          </Field>
          <Field label="Your response">
            <textarea
              className="input"
              value={form.tenant_response}
              onChange={(e) => set("tenant_response", e.target.value)}
              style={{ width: "100%", minHeight: 60 }}
            />
          </Field>
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
            <button className="btn" onClick={submit} disabled={submitting}>
              {submitting ? "GENERATING…" : "GENERATE DEMAND LETTER"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label>
      <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
        {label}
      </span>
      {children}
    </label>
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
