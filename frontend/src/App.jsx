import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import UploadFlow from "./pages/UploadFlow";
import ResultsPage from "./pages/ResultsPage";
import ExpungementPage from "./pages/ExpungementPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadFlow />} />
        <Route path="/results/:documentId" element={<ResultsPage />} />
        <Route path="/expungement" element={<ExpungementPage />} />
        {/* /pay/:id and /subscribe will be added in a later prompt */}
      </Routes>
    </BrowserRouter>
  );
}
