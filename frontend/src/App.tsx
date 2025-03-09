import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/lib/locale/zh_CN';
import { useAuthStore } from './stores/authStore';
import LoginPage from './pages/LoginPage';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import LedgerList from './pages/ledger/LedgerList';
import LedgerForm from './pages/ledger/LedgerForm';
import LedgerDetail from './pages/ledger/LedgerDetail';
import TemplateList from './pages/template/TemplateList';
import TemplateForm from './pages/template/TemplateForm';
import TemplateLedgerSummary from './pages/template/TemplateLedgerSummary';
import UserManagementFixed from './pages/admin/UserManagementFixed';
import RoleManagement from './pages/admin/RoleManagement';
import PermissionManagement from './pages/admin/PermissionManagement';
import TeamManagement from './pages/admin/TeamManagement';
import TeamMembers from './pages/admin/TeamMembers';
import WorkflowList from './pages/workflow/WorkflowList';
import WorkflowForm from './pages/workflow/WorkflowForm';
import WorkflowDetail from './pages/workflow/WorkflowDetail';
import TaskList from './pages/approval/TaskList';
import LogList from './pages/log/LogList';
import HelpPage from './pages/HelpPage';
import PasswordExpiredModal from './components/PasswordExpiredModal';
import './App.css';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <>
                  <Layout />
                  <PasswordExpiredModal />
                </>
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="ledgers" element={<LedgerList />} />
            <Route path="ledgers/new" element={<LedgerForm />} />
            <Route path="ledgers/edit/:id" element={<LedgerForm />} />
            <Route path="ledgers/:id" element={<LedgerDetail />} />
            <Route path="templates" element={<TemplateList />} />
            <Route path="templates/new" element={<TemplateForm />} />
            <Route path="templates/edit/:id" element={<TemplateForm />} />
            <Route path="templates/:templateId/ledgers" element={<TemplateLedgerSummary />} />
            <Route path="workflow" element={<WorkflowList />} />
            <Route path="workflow/create" element={<WorkflowForm />} />
            <Route path="workflow/edit/:id" element={<WorkflowForm />} />
            <Route path="workflow/:id" element={<WorkflowDetail />} />
            <Route path="approval/tasks" element={<TaskList />} />
            <Route path="logs" element={<LogList />} />
            <Route path="admin/users" element={<UserManagementFixed />} />
            <Route path="admin/roles" element={<RoleManagement />} />
            <Route path="admin/permissions" element={<PermissionManagement />} />
            <Route path="admin/teams" element={<TeamManagement />} />
            <Route path="admin/teams/:id/members" element={<TeamMembers />} />
            <Route path="help" element={<HelpPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
