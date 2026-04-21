import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import UploadFlow from "./pages/UploadFlow";
import ResultsPage from "./pages/ResultsPage";
import ExpungementPage from "./pages/ExpungementPage";
import PaywallPage from "./pages/PaywallPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadFlow />} />
        <Route path="/results/:documentId" element={<ResultsPage />} />
        <Route path="/expungement" element={<ExpungementPage />} />
        <Route path="/pay/:documentId" element={<PaywallPage />} />
      </Routes>
    </BrowserRouter>
  );
}
