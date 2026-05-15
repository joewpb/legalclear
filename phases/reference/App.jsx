import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import LandingPage from './pages/LandingPage';
import UploadFlow from './pages/UploadFlow';
import AnalysisDashboard from './pages/AnalysisDashboard';
import EligibilityPage from './pages/EligibilityPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col selection:bg-primary/30">
        <Navbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/upload" element={<UploadFlow />} />
            <Route path="/dashboard" element={<AnalysisDashboard />} />
            <Route path="/eligibility" element={<EligibilityPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
