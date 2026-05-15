type Props = {
  packetId: string;
  feeUsd: number;
  checkoutUrl: string | null;
  language: "en" | "es";
};

const COPY = {
  en: {
    heading: "Pay $35 to download your packet",
    body:
      "LegalClear charges a flat $35 per filing packet. Payment unlocks the 3-PDF download and the manual upload walkthrough.",
    button: "PAY $35 → STRIPE CHECKOUT",
    noUrl: "Stripe checkout unavailable. Refresh the page to try again.",
    note:
      "The county filing fee shown above is separate — you pay the clerk directly on the e-filing portal.",
  },
  es: {
    heading: "Pague $35 para descargar su paquete",
    body:
      "LegalClear cobra una tarifa fija de $35 por cada paquete de presentación. El pago desbloquea la descarga de los 3 PDF y la guía de carga manual.",
    button: "PAGAR $35 → STRIPE",
    noUrl: "Stripe no disponible. Actualice la página para intentarlo de nuevo.",
    note:
      "La tarifa de presentación del condado mostrada arriba es independiente; se paga directamente al secretario en el portal de presentación electrónica.",
  },
};

export default function PaymentGate({
  feeUsd,
  checkoutUrl,
  language,
}: Props) {
  const t = COPY[language];
  return (
    <section
      style={{
        border: "2px solid var(--accent)",
        padding: 24,
        display: "grid",
        gap: 12,
      }}
    >
      <h2 className="mono" style={{ fontSize: 18, margin: 0 }}>
        {t.heading}
      </h2>
      <p style={{ margin: 0 }}>{t.body}</p>
      <p style={{ color: "var(--muted)", margin: 0, fontSize: 13 }}>
        {t.note} (${feeUsd.toFixed(2)} county fee shown above.)
      </p>
      {checkoutUrl ? (
        <a
          href={checkoutUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn"
          style={{ justifySelf: "start", textDecoration: "none" }}
        >
          {t.button}
        </a>
      ) : (
        <p role="alert" style={{ color: "var(--danger)", margin: 0 }}>
          {t.noUrl}
        </p>
      )}
    </section>
  );
}
