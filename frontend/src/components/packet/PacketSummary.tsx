import type { PacketMetadata } from "./types";

type Props = {
  packet: PacketMetadata;
  language: "en" | "es";
};

const COPY = {
  en: {
    heading: "Your filing packet",
    type: "Type",
    county: "County",
    fee: "Filing fee",
    status: "Status",
    files: "Files",
    pending: "PENDING PAYMENT",
    paid: "PAID",
    typeLabels: {
      small_claims: "Small claims",
      expungement: "Expungement",
      landlord_deposit: "Security deposit demand",
      landlord_repairs: "Repairs notice",
      landlord_eviction: "Eviction answer",
      traffic: "Traffic hearing request",
    } as Record<string, string>,
  },
  es: {
    heading: "Su paquete de presentación",
    type: "Tipo",
    county: "Condado",
    fee: "Tarifa de presentación",
    status: "Estado",
    files: "Archivos",
    pending: "PAGO PENDIENTE",
    paid: "PAGADO",
    typeLabels: {
      small_claims: "Reclamos menores",
      expungement: "Cancelación de antecedentes",
      landlord_deposit: "Reclamo de depósito de garantía",
      landlord_repairs: "Notificación de reparaciones",
      landlord_eviction: "Contestación de desalojo",
      traffic: "Solicitud de audiencia de tránsito",
    } as Record<string, string>,
  },
};

export default function PacketSummary({ packet, language }: Props) {
  const t = COPY[language];
  const typeLabel = t.typeLabels[packet.packet_type] || packet.packet_type;
  const paid = packet.status === "paid";

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
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "160px 1fr",
          rowGap: 6,
          columnGap: 16,
          margin: 0,
          fontSize: 14,
        }}
      >
        <dt className="mono" style={{ color: "var(--muted)" }}>{t.type}</dt>
        <dd>{typeLabel}</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>{t.county}</dt>
        <dd>{packet.county}</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>{t.fee}</dt>
        <dd>${packet.fee_usd.toFixed(2)}</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>{t.files}</dt>
        <dd>3 PDF (PDF/A-1b)</dd>
        <dt className="mono" style={{ color: "var(--muted)" }}>{t.status}</dt>
        <dd
          className="mono"
          style={{
            color: paid ? "var(--success)" : "var(--accent)",
            letterSpacing: "0.06em",
          }}
        >
          {paid ? t.paid : t.pending}
        </dd>
      </dl>
    </section>
  );
}
