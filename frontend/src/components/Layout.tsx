import React, { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Dropdown, Button, theme } from 'antd';
import {
  UserOutlined,
  DashboardOutlined,
  FileOutlined,
  FormOutlined,
  TeamOutlined,
  SettingOutlined,
  SafetyOutlined,
  AuditOutlined,
  LogoutOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  QuestionCircleOutlined,
  FileSearchOutlined,
  FieldBinaryOutlined,
  SolutionOutlined,
} from '@ant-design/icons';
import { useNavigate, Outlet, useLocation, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { PERMISSIONS } from '../config';

const { Header, Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [openKeys, setOpenKeys] = useState<string[]>(['admin']);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, hasPermission } = useAuthStore();
  const { token } = theme.useToken();

  // 当路由变化时，更新选中的菜单项
  useEffect(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    
    // 默认选中仪表盘
    if (pathSegments.length === 0 || (pathSegments[0] === 'dashboard' && pathSegments.length === 1)) {
      setSelectedKeys(['dashboard']);
      return;
    }
    
    // 从路径中提取菜单key
    if (pathSegments.length >= 1) {
      if (pathSegments[0] === 'dashboard' && pathSegments.length >= 2) {
        // 处理子菜单的情况
        if (pathSegments[1] === 'admin' && pathSegments.length >= 3) {
          // 系统管理子菜单
          setSelectedKeys([pathSegments[2]]);
          setOpenKeys(['admin']);
        } else {
          // 普通菜单
          setSelectedKeys([pathSegments[1]]);
        }
      } else {
        // 非dashboard开头的路径
        setSelectedKeys([pathSegments[0]]);
      }
    }
  }, [location]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // 处理子菜单展开状态
  const onOpenChange = (keys: string[]) => {
    setOpenKeys(keys);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          backgroundColor: token.colorBgContainer,
          boxShadow: '2px 0 8px rgba(0,0,0,0.06)'
        }}
      >
        <div 
          style={{ 
            height: 64, 
            margin: 16, 
            textAlign: 'center', 
            lineHeight: '32px',
            fontSize: collapsed ? 14 : 18,
            fontWeight: 'bold',
            color: token.colorPrimary
          }}
        >
          {collapsed ? '台账' : '台账管理系统'}
        </div>
        
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={selectedKeys}
          openKeys={!collapsed ? openKeys : []}
          onOpenChange={onOpenChange}
          items={[
            // 仪表盘
            {
              key: 'dashboard',
              icon: <DashboardOutlined />,
              label: <Link to="/dashboard">仪表盘</Link>,
            },
            
            // 台账管理
            hasPermission(PERMISSIONS.LEDGER_VIEW) ? {
              key: 'ledgers',
              icon: <FileOutlined />,
              label: <Link to="/dashboard/ledgers">台账管理</Link>,
            } : null,
            
            // 模板管理
            hasPermission(PERMISSIONS.TEMPLATE_VIEW) ? {
              key: 'templates',
              icon: <FormOutlined />,
              label: <Link to="/dashboard/templates">模板管理</Link>,
            } : null,
            
            // 工作流管理
            hasPermission(PERMISSIONS.WORKFLOW_VIEW) ? {
              key: 'workflow',
              icon: <FieldBinaryOutlined />,
              label: <Link to="/dashboard/workflow">工作流管理</Link>,
            } : null,
            
            // 审批任务
            hasPermission(PERMISSIONS.APPROVAL_VIEW) ? {
              key: 'approval',
              icon: <SolutionOutlined />,
              label: <Link to="/dashboard/approval/tasks">审批任务</Link>,
            } : null,
            
            // 日志管理
            hasPermission(PERMISSIONS.LOG_VIEW) ? {
              key: 'logs',
              icon: <FileSearchOutlined />,
              label: <Link to="/dashboard/logs">日志管理</Link>,
            } : null,
            
            // 系统管理
            (hasPermission(PERMISSIONS.USER_VIEW) || 
             hasPermission(PERMISSIONS.ROLE_VIEW) ||
             hasPermission(PERMISSIONS.TEAM_VIEW) ||
             hasPermission(PERMISSIONS.PERMISSION_VIEW)) ? {
              key: 'admin',
              icon: <SettingOutlined />,
              label: '系统管理',
              children: [
                hasPermission(PERMISSIONS.USER_VIEW) ? {
                  key: 'users',
                  icon: <UserOutlined />,
                  label: <Link to="/dashboard/admin/users">用户管理</Link>,
                } : null,
                hasPermission(PERMISSIONS.ROLE_VIEW) ? {
                  key: 'roles',
                  icon: <SafetyOutlined />,
                  label: <Link to="/dashboard/admin/roles">角色管理</Link>,
                } : null,
                hasPermission(PERMISSIONS.TEAM_VIEW) ? {
                  key: 'teams',
                  icon: <TeamOutlined />,
                  label: <Link to="/dashboard/admin/teams">团队管理</Link>,
                } : null,
                hasPermission(PERMISSIONS.PERMISSION_VIEW) ? {
                  key: 'permissions',
                  icon: <AuditOutlined />,
                  label: <Link to="/dashboard/admin/permissions">权限管理</Link>,
                } : null,
              ].filter(Boolean),
            } : null,
            
            // 帮助
            {
              key: 'help',
              icon: <QuestionCircleOutlined />,
              label: <Link to="/dashboard/help">帮助</Link>,
            },
          ].filter(Boolean)}
        />
      </Sider>
      
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.3s' }}>
        <Header 
          style={{ 
            padding: 0, 
            background: token.colorBgContainer, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,0,0,0.05)'
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />
          
          <div style={{ paddingRight: 24 }}>
            <Dropdown menu={{ 
              items: [
                {
                  key: 'profile',
                  icon: <UserOutlined />,
                  label: '个人中心',
                  onClick: () => navigate('/dashboard/user-profile')
                },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: handleLogout
                }
              ]
            }}>
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} />
                <span>{user?.name || user?.username}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        
        <Content style={{ margin: '24px 16px', padding: 24, background: token.colorBgContainer, borderRadius: token.borderRadius, minHeight: 280 }}>
          <div id="breadcrumb-container" style={{ marginBottom: 16 }}>
            {/* 面包屑导航将由各页面组件填充 */}
          </div>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout; 