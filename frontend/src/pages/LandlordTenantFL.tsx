import { Link, Routes, Route } from "react-router-dom";
import HubTile from "../components/HubTile";
import DepositFlow from "../components/landlord/DepositFlow";
import RepairsFlow from "../components/landlord/RepairsFlow";
import EvictionFlow from "../components/landlord/EvictionFlow";

const SUB_FLOWS = [
  {
    title: "DEPOSIT NOT RETURNED",
    subtitle: "Demand letter under FL §83.49",
    to: "/landlord/deposit",
  },
  {
    title: "REPAIRS NOT MADE",
    subtitle: "7-day notice under FL §83.56(1)",
    to: "/landlord/repairs",
  },
  {
    title: "EVICTION DEFENSE",
    subtitle: "Answer to complaint under FL §83.60",
    to: "/landlord/eviction",
  },
];

function Landing() {
  return (
    <>
      <header className="hub-header">
        <h1>LANDLORD / TENANT (FL)</h1>
        <p>Pick the situation you're in.</p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>
      <main className="hub-main">
        <div className="hub-grid">
          {SUB_FLOWS.map((s) => (
            <HubTile
              key={s.to}
              title={s.title}
              subtitle={s.subtitle}
              to={s.to}
            />
          ))}
        </div>
      </main>
    </>
  );
}

function SubFlowFrame({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <header className="hub-header">
        <h1>{title}</h1>
        <p style={{ marginTop: 8 }}>
          <Link
            to="/landlord"
            style={{ color: "var(--muted)", fontSize: 12 }}
          >
            ← Back to landlord/tenant
          </Link>
        </p>
      </header>
      <main className="hub-main">{children}</main>
    </>
  );
}

export default function LandlordTenantFL() {
  return (
    <>
      <Routes>
        <Route index element={<Landing />} />
        <Route
          path="deposit"
          element={
            <SubFlowFrame title="DEPOSIT NOT RETURNED (FL §83.49)">
              <DepositFlow />
            </SubFlowFrame>
          }
        />
        <Route
          path="repairs"
          element={
            <SubFlowFrame title="REPAIRS NOT MADE (FL §83.56)">
              <RepairsFlow />
            </SubFlowFrame>
          }
        />
        <Route
          path="eviction"
          element={
            <SubFlowFrame title="EVICTION DEFENSE (FL §83.60)">
              <EvictionFlow />
            </SubFlowFrame>
          }
        />
      </Routes>
      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Nothing here is legal
          advice. Using this site does not create an attorney-client
          relationship. For your specific situation, consult a licensed Florida
          attorney.
        </p>
      </footer>
    </>
  );
}
