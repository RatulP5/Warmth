import DashboardLayout from './components/layouts/DashboardLayout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Alerts from './pages/Alerts.jsx'
import Analytics from './pages/Analytics.jsx'
import WardIntelligence from './pages/WardIntelligence.jsx'
import { Navigate, Route, Routes } from 'react-router-dom'

export default function App() {
  return (
    <div>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ward-intelligence" element={<WardIntelligence />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </DashboardLayout>
    </div>
);
}
