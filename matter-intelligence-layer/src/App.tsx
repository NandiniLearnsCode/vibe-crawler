import { Navigate, Route, Routes } from 'react-router-dom';
import { TopNav } from './components/layout/TopNav';
import { ClientSharedSpacePage } from './pages/ClientSharedSpacePage';
import { CloseAndLearnPage } from './pages/CloseAndLearnPage';
import { MatterOverviewPage } from './pages/MatterOverviewPage';
import { MattersListPage } from './pages/MattersListPage';
import { RiskDetailPage } from './pages/RiskDetailPage';
import { WorkstreamDetailPage } from './pages/WorkstreamDetailPage';

function App() {
  return (
    <>
      <TopNav />
      <Routes>
        <Route path="/matters" element={<MattersListPage />} />
        <Route path="/matters/:matterId" element={<MatterOverviewPage />} />
        <Route path="/matters/:matterId/workstreams/:workstreamId" element={<WorkstreamDetailPage />} />
        <Route path="/matters/:matterId/risks/:riskId" element={<RiskDetailPage />} />
        <Route path="/matters/:matterId/client-view" element={<ClientSharedSpacePage />} />
        <Route path="/matters/:matterId/close-learn" element={<CloseAndLearnPage />} />
        <Route path="*" element={<Navigate to="/matters" replace />} />
      </Routes>
    </>
  );
}

export default App;
