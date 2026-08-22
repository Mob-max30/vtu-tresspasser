import { Routes, Route, NavLink } from 'react-router-dom';
import SetupPage from './pages/SetupPage.jsx';
import AgentRunningPage from './pages/AgentRunningPage.jsx';
import ResultsPage from './pages/ResultsPage.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';

export default function App() {
  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 960, margin: '0 auto', padding: 24 }}>
      <h1>VTU Result Intelligence Agent</h1>
      <nav style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <NavLink to="/">Setup</NavLink>
        <NavLink to="/agent">Agent Running</NavLink>
        <NavLink to="/results">Results</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<SetupPage />} />
        <Route path="/agent" element={<AgentRunningPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Routes>
    </div>
  );
}
