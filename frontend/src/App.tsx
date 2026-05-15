import { BrowserRouter, Routes, Route } from "react-router-dom";

// Hub (Phase 15)
import HomeHub from "./pages/HomeHub";
import PhaseStub from "./pages/PhaseStub";

// Part B tile pages
import SmallClaimsFL from "./pages/SmallClaimsFL"; // Phase 16

// Existing Part A / Part B-in-progress pages — kept as-is per Phase 15
// "do not touch existing FastAPI routes / existing pages" rule.
// The /expungement route still points at the multi-state ExpungementPage
// for now; Phase 17 replaces it with the FL-only ExpungementFL.tsx.
// @ts-expect-error — pre-existing .jsx with no types; allowJs covers it
import UploadFlow from "./pages/UploadFlow";
// @ts-expect-error — pre-existing .jsx with no types
import ResultsPage from "./pages/ResultsPage";
// @ts-expect-error — pre-existing .jsx with no types
import ExpungementPage from "./pages/ExpungementPage";
// @ts-expect-error — pre-existing .jsx with no types
import PaywallPage from "./pages/PaywallPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Phase 15 — new hub at / */}
        <Route path="/" element={<HomeHub />} />

        {/* Tile 1 — existing uploader (Phase 12) */}
        <Route path="/upload" element={<UploadFlow />} />

        {/* Tile 3 — existing expungement page (Phase 17 will replace) */}
        <Route path="/expungement" element={<ExpungementPage />} />

        {/* Tile 2 — Phase 16 */}
        <Route path="/small-claims" element={<SmallClaimsFL />} />

        {/* Tiles 4, 5, 6, 7, 8 — stubs until their phase builds them */}
        <Route
          path="/landlord"
          element={
            <PhaseStub title="LANDLORD / TENANT (FL)" phase="Phase 18" />
          }
        />
        <Route
          path="/forms"
          element={
            <PhaseStub title="COURT FORMS FINDER (FL)" phase="Phase 19" />
          }
        />
        <Route
          path="/traffic"
          element={
            <PhaseStub title="TRAFFIC / TICKETS (FL)" phase="Phase 20" />
          }
        />
        <Route
          path="/police-report"
          element={
            <PhaseStub title="POLICE REPORT ANALYZER" phase="Phase 21" />
          }
        />
        <Route
          path="/case-law"
          element={<PhaseStub title="FL CASE LAW LOOKUP" phase="Phase 22" />}
        />

        {/* Existing routes preserved (Phase 12 era) */}
        <Route path="/results/:documentId" element={<ResultsPage />} />
        <Route path="/pay/:documentId" element={<PaywallPage />} />
      </Routes>
    </BrowserRouter>
  );
}
