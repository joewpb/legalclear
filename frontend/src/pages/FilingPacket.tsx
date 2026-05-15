import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import FilingTracker from "../components/packet/FilingTracker";
import LanguageToggle, {
  readLanguage,
  type Language,
} from "../components/packet/LanguageToggle";
import PacketSummary from "../components/packet/PacketSummary";
import PaymentGate from "../components/packet/PaymentGate";
import UploadWalkthrough from "../components/packet/UploadWalkthrough";
import type { PacketMetadata } from "../components/packet/types";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

const COPY = {
  en: {
    title: "Filing packet",
    backToHub: "← BACK TO HUB",
    loading: "Loading packet metadata...",
    notFound: "Packet not found. It may have expired or never been created.",
    download: "DOWNLOAD ZIP (3 PDFs)",
    downloadFailed: "Download failed",
  },
  es: {
    title: "Paquete de presentación",
    backToHub: "← VOLVER AL INICIO",
    loading: "Cargando metadatos del paquete...",
    notFound: "Paquete no encontrado. Es posible que haya caducado o que nunca se haya creado.",
    download: "DESCARGAR ZIP (3 PDF)",
    downloadFailed: "La descarga falló",
  },
};

export default function FilingPacket() {
  const { packetId = "" } = useParams<{ packetId: string }>();
  const [params] = useSearchParams();
  const paid = params.get("paid") === "1";
  const checkoutUrlFromState =
    typeof window !== "undefined"
      ? sessionStorage.getItem(`lc.packet.${packetId}.checkout_url`)
      : null;

  const [language, setLanguage] = useState<Language>(() => readLanguage());
  const [packet, setPacket] = useState<PacketMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // If we just came back from Stripe with ?paid=1, flip the in-memory
      // status flag on the backend (dev-only convenience; the webhook in
      // routes.py is the production path).
      if (paid) {
        try {
          await fetch(`${API_URL}/api/packet/${packetId}/mark_paid`, {
            method: "POST",
          });
        } catch {
          /* non-fatal */
        }
      }
      const r = await fetch(`${API_URL}/api/packet/${packetId}`);
      if (r.status === 404) {
        setError(COPY[language].notFound);
        setPacket(null);
      } else if (!r.ok) {
        throw new Error(`Server returned ${r.status}`);
      } else {
        setPacket((await r.json()) as PacketMetadata);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [packetId, paid, language]);

  useEffect(() => {
    void load();
  }, [load]);

  const t = COPY[language];

  async function downloadZip() {
    try {
      const r = await fetch(`${API_URL}/api/packet/${packetId}/download`);
      if (!r.ok) throw new Error(`${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `legalclear_packet_${packetId}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(`${t.downloadFailed}: ${(e as Error).message}`);
    }
  }

  return (
    <main
      className="container"
      style={{ padding: 24, maxWidth: 880, margin: "0 auto", display: "grid", gap: 20 }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 className="mono" style={{ fontSize: 22, margin: 0 }}>
          {t.title}
        </h1>
        <LanguageToggle value={language} onChange={setLanguage} />
      </header>

      <a
        href="/"
        className="mono"
        style={{
          fontSize: 12,
          letterSpacing: "0.08em",
          color: "var(--muted)",
          textDecoration: "none",
        }}
      >
        {t.backToHub}
      </a>

      {loading && (
        <p className="mono" style={{ color: "var(--muted)" }}>
          {t.loading}
        </p>
      )}

      {error && !packet && (
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

      {packet && (
        <>
          <PacketSummary packet={packet} language={language} />

          {packet.status !== "paid" && (
            <PaymentGate
              packetId={packetId}
              feeUsd={packet.fee_usd}
              checkoutUrl={checkoutUrlFromState}
              language={language}
            />
          )}

          {packet.status === "paid" && (
            <>
              <section
                style={{
                  border: "2px solid var(--success)",
                  padding: 24,
                  display: "grid",
                  gap: 12,
                }}
              >
                <h2 className="mono" style={{ fontSize: 18, margin: 0 }}>
                  {language === "es"
                    ? "Pago confirmado. Descargue su paquete."
                    : "Payment confirmed. Download your packet."}
                </h2>
                <button
                  className="btn"
                  onClick={downloadZip}
                  style={{ justifySelf: "start" }}
                >
                  {t.download}
                </button>
              </section>
              <UploadWalkthrough language={language} />
              <FilingTracker
                packetId={packetId}
                language={language}
                initialConfirmation={packet.confirmation_number}
                initialFiledAt={packet.filed_at}
              />
            </>
          )}
        </>
      )}
    </main>
  );
}
