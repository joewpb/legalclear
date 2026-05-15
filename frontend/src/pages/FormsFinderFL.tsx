import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import formsIndex from "../data/fl_courts_forms_index.json";

type FormEntry = {
  name: string;
  form_number: string;
  url: string;
};

type IndexEntry = {
  case_type: string;
  sub_category: string;
  forms: FormEntry[];
};

const INDEX = formsIndex as IndexEntry[];

const CASE_TYPES = [
  "Family",
  "Civil",
  "Probate",
  "Small Claims",
  "Traffic",
  "Criminal",
] as const;

export default function FormsFinderFL() {
  const [caseType, setCaseType] = useState<string | null>(null);
  const [subCategory, setSubCategory] = useState<string | null>(null);

  const subCategories = useMemo(() => {
    if (!caseType) return [];
    return INDEX.filter((e) => e.case_type === caseType).map(
      (e) => e.sub_category,
    );
  }, [caseType]);

  const forms = useMemo(() => {
    if (!caseType || !subCategory) return [];
    const entry = INDEX.find(
      (e) => e.case_type === caseType && e.sub_category === subCategory,
    );
    return entry?.forms ?? [];
  }, [caseType, subCategory]);

  return (
    <>
      <header className="hub-header">
        <h1>COURT FORMS FINDER (FL)</h1>
        <p>Pick a case type, then a sub-category, to see official FL forms.</p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        <Stepper caseType={caseType} subCategory={subCategory} />

        {!caseType && (
          <Section title="STEP 1 — CASE TYPE">
            <div
              className="hub-grid"
              role="list"
              aria-label="Case types"
            >
              {CASE_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  className="hub-tile"
                  onClick={() => setCaseType(t)}
                  style={{ textAlign: "left", cursor: "pointer" }}
                >
                  <h2 className="hub-tile__title">{t.toUpperCase()}</h2>
                  <p className="hub-tile__subtitle">
                    {countFor(t)} sub-categories
                  </p>
                </button>
              ))}
            </div>
          </Section>
        )}

        {caseType && !subCategory && (
          <Section title={`STEP 2 — ${caseType.toUpperCase()} SUB-CATEGORY`}>
            <div style={{ display: "grid", gap: 12, padding: 32 }}>
              {subCategories.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="btn"
                  onClick={() => setSubCategory(s)}
                  style={{ textAlign: "left" }}
                >
                  {s.toUpperCase()}
                </button>
              ))}
              <button
                type="button"
                className="btn"
                onClick={() => setCaseType(null)}
                style={{ marginTop: 16, alignSelf: "flex-start" }}
              >
                ← BACK TO CASE TYPES
              </button>
            </div>
          </Section>
        )}

        {caseType && subCategory && (
          <Section title={`${caseType.toUpperCase()} — ${subCategory.toUpperCase()}`}>
            <div style={{ display: "grid", gap: 16, padding: 32 }}>
              {forms.map((f) => (
                <article
                  key={`${f.form_number}-${f.name}`}
                  style={{
                    border: "1px solid var(--border)",
                    padding: 16,
                    display: "grid",
                    gap: 6,
                  }}
                >
                  <h3 className="mono" style={{ fontSize: 16, margin: 0 }}>
                    {f.name}
                  </h3>
                  <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
                    Form ref:{" "}
                    <span className="mono">{f.form_number}</span>
                  </p>
                  <a
                    href={f.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn"
                    style={{
                      justifySelf: "start",
                      textDecoration: "none",
                      marginTop: 8,
                    }}
                  >
                    OPEN OFFICIAL PAGE →
                  </a>
                </article>
              ))}
              {forms.length === 0 && (
                <p style={{ color: "var(--muted)" }}>
                  No forms catalogued for this sub-category yet.
                </p>
              )}
              <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setSubCategory(null)}
                >
                  ← CHANGE SUB-CATEGORY
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setCaseType(null);
                    setSubCategory(null);
                  }}
                >
                  ← CHANGE CASE TYPE
                </button>
              </div>
            </div>
          </Section>
        )}
      </main>

      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Links point to official
          Florida court / state agency pages. Nothing here is legal advice.
          Using this site does not create an attorney-client relationship.
        </p>
      </footer>
    </>
  );
}

function countFor(t: string) {
  return INDEX.filter((e) => e.case_type === t).length;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 24 }}>
      <h2
        className="mono"
        style={{
          fontSize: 14,
          letterSpacing: "0.08em",
          padding: "12px 32px",
          borderBottom: "1px solid var(--border)",
          margin: 0,
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function Stepper({
  caseType,
  subCategory,
}: {
  caseType: string | null;
  subCategory: string | null;
}) {
  const step = subCategory ? 3 : caseType ? 2 : 1;
  return (
    <div style={{ padding: "0 32px 16px" }}>
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
