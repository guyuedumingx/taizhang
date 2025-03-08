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
import UserManagement from './pages/admin/UserManagement';
import RoleManagement from './pages/admin/RoleManagement';
import PermissionManagement from './pages/admin/PermissionManagement';
import TeamManagement from './pages/admin/TeamManagement';
import HelpPage from './pages/HelpPage';
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
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
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
            <Route path="admin/users" element={<UserManagement />} />
            <Route path="admin/roles" element={<RoleManagement />} />
            <Route path="admin/permissions" element={<PermissionManagement />} />
            <Route path="admin/teams" element={<TeamManagement />} />
            <Route path="help" element={<HelpPage />} />
          </Route>
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
