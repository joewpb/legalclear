import { Link } from "react-router-dom";
import { WizardProvider, useWizard } from "../components/smallclaims/WizardContext";
import ProgressBar from "../components/smallclaims/ProgressBar";
import ClaimTypeStep from "../components/smallclaims/ClaimTypeStep";
import AmountStep from "../components/smallclaims/AmountStep";
import DefendantStep from "../components/smallclaims/DefendantStep";
import CountyStep from "../components/smallclaims/CountyStep";
import ReviewStep from "../components/smallclaims/ReviewStep";

function ActiveStep() {
  const { step } = useWizard();
  switch (step) {
    case 1:
      return <ClaimTypeStep />;
    case 2:
      return <AmountStep />;
    case 3:
      return <DefendantStep />;
    case 4:
      return <CountyStep />;
    case 5:
      return <ReviewStep />;
    default:
      return <ClaimTypeStep />;
  }
}

export default function SmallClaimsFL() {
  return (
    <WizardProvider>
      <header className="hub-header">
        <h1>SMALL CLAIMS (FL)</h1>
        <p>File a claim for up to $8,000 in Florida.</p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>
      <ProgressBar />
      <main className="hub-main">
        <ActiveStep />
      </main>
      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Nothing here is legal
          advice. Using this site does not create an attorney-client
          relationship. For your specific situation, consult a licensed Florida
          attorney.
        </p>
      </footer>
    </WizardProvider>
  );
}
