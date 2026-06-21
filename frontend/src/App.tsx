import { BrowserRouter, Routes, Route } from "react-router-dom";

// Shared chrome (v1 retheme)
import SiteHeader from "./components/SiteHeader";
import SiteFooter from "./components/SiteFooter";

// Hub (Phase 15)
import HomeHub from "./pages/HomeHub";

// Part B tile pages
import SmallClaimsFL from "./pages/SmallClaimsFL"; // Phase 16 (filing wizard)
import SmallClaimsExplainer from "./pages/SmallClaimsExplainer"; // Module 1 (v3 explainer)
import CriminalProcedureExplainer from "./pages/CriminalProcedureExplainer"; // Module 2 (v3 explainer)
import DiscoveryMotionAnalyzer from "./pages/DiscoveryMotionAnalyzer"; // Module 4 (v3 explainer)
import PropertyCasualtyExplainer from "./pages/PropertyCasualtyExplainer"; // Module 5 (v3 explainer)
import ExpungementFL from "./pages/ExpungementFL"; // Phase 17
import LandlordTenantFL from "./pages/LandlordTenantFL"; // Phase 18
import FormsFinderFL from "./pages/FormsFinderFL"; // Phase 19
import TrafficFL from "./pages/TrafficFL"; // Phase 20
import PoliceReportAnalyzer from "./pages/PoliceReportAnalyzer"; // Phase 21
import CaseLawLookupFL from "./pages/CaseLawLookupFL"; // Phase 22
import FilingPacket from "./pages/FilingPacket"; // Phase 23

// Existing Part A / Part B-in-progress pages — kept as-is per Phase 15
// "do not touch existing FastAPI routes / existing pages" rule.
// The /expungement route still points at the multi-state ExpungementPage
// for now; Phase 17 replaces it with the FL-only ExpungementFL.tsx.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const UploadFlow = require("./pages/UploadFlow").default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const ResultsPage = require("./pages/ResultsPage").default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const PaywallPage = require("./pages/PaywallPage").default;

export default function App() {
  return (
    <BrowserRouter>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          minHeight: "100vh",
        }}
      >
        <SiteHeader />
        <main style={{ flex: 1 }}>
          <Routes>
        {/* Phase 15 — new hub at / */}
        <Route path="/" element={<HomeHub />} />

        {/* Tile 1 — existing uploader (Phase 12) */}
        <Route path="/upload" element={<UploadFlow />} />

        {/* Tile 3 — Phase 17 (replaces the old multi-state ExpungementPage.jsx) */}
        <Route path="/expungement" element={<ExpungementFL />} />

        {/* v3 Module 1 — Small Claims Explainer (AI-first) */}
        <Route path="/small-claims" element={<SmallClaimsExplainer />} />

        {/* Tile 2 — Phase 16 filing wizard (linked from explainer) */}
        <Route path="/small-claims/file" element={<SmallClaimsFL />} />

        {/* v3 Module 2 — Criminal Procedure Explainer */}
        <Route path="/criminal-procedure" element={<CriminalProcedureExplainer />} />

        {/* v3 Module 4 — Discovery Motion Analyzer */}
        <Route path="/discovery-motion" element={<DiscoveryMotionAnalyzer />} />

        {/* v3 Module 5 — Property & Casualty Explainer */}
        <Route path="/property-casualty" element={<PropertyCasualtyExplainer />} />

        {/* Tile 4 — Phase 18 (landing + 3 sub-flows; sub-routes handled inside) */}
        <Route path="/landlord/*" element={<LandlordTenantFL />} />

        {/* Tile 5 — Phase 19 (data-driven forms lookup) */}
        <Route path="/forms" element={<FormsFinderFL />} />

        {/* Tile 6 — Phase 20 (3-path traffic wizard) */}
        <Route path="/traffic" element={<TrafficFL />} />

        {/* Tile 7 — Phase 21 (police report analyzer) */}
        <Route path="/police-report" element={<PoliceReportAnalyzer />} />

        {/* Tile 8 — Phase 22 (FL case law via CourtListener) */}
        <Route path="/case-law" element={<CaseLawLookupFL />} />

        {/* Phase 23 — Filing Packet (Stripe-gated download + tracker) */}
        <Route path="/filing-packet/:packetId" element={<FilingPacket />} />

        {/* Existing routes preserved (Phase 12 era) */}
        <Route path="/results/:documentId" element={<ResultsPage />} />
        <Route path="/pay/:documentId" element={<PaywallPage />} />
          </Routes>
        </main>
        <SiteFooter />
      </div>
    </BrowserRouter>
  );
}
