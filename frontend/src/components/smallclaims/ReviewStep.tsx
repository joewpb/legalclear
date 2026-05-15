import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../packet/LanguageToggle";
import { useWizard } from "./WizardContext";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

// Phase 23 — /api/small-claims/generate now returns a packet_id + Stripe
// checkout URL. The page navigates to /filing-packet/:packetId; the
// checkout URL is stashed in sessionStorage so the PaymentGate on that
// page can link to it directly.
type GenerateResult = {
  packet_id: string;
  fee_usd: number;
  file_count: number;
  checkout_url: string;
};

export default function ReviewStep() {
  const { data, back } = useWizard();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>(() => readLanguage());

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
      setLoading(false);
    }
  }

  return (
    <section style={{ padding: 32 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
          Review your claim
        </h2>
        <LanguageToggle value={language} onChange={setLanguage} />
      </div>
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
