import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Button, Dropdown, Avatar, theme, Typography } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  FileTextOutlined,
  FormOutlined,
  TeamOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, Outlet, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { PERMISSIONS } from '../config';

const { Header, Sider, Content, Footer } = AntLayout;
const { Title } = Typography;

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();
  const navigate = useNavigate();
  const { user, logout, hasPermission } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed} 
        width={240}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div className="logo" style={{ 
          height: 64, 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          color: 'white', 
          fontSize: collapsed ? 16 : 20, 
          fontWeight: 'bold',
          margin: '16px 0'
        }}>
          {collapsed ? 'TZ' : '台账管理系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          defaultSelectedKeys={['dashboard']}
          items={[
            {
              key: 'dashboard',
              icon: <DashboardOutlined />,
              label: <Link to="/">首页</Link>,
            },
            {
              key: 'ledgers',
              icon: <FileTextOutlined />,
              label: <Link to="/ledgers">台账管理</Link>,
              disabled: !hasPermission(PERMISSIONS.LEDGER_VIEW),
            },
            {
              key: 'templates',
              icon: <FormOutlined />,
              label: <Link to="/templates">模板管理</Link>,
              disabled: !hasPermission(PERMISSIONS.TEMPLATE_VIEW),
            },
            {
              key: 'admin',
              icon: <SettingOutlined />,
              label: '系统管理',
              disabled: !(
                hasPermission(PERMISSIONS.USER_VIEW) ||
                hasPermission(PERMISSIONS.ROLE_VIEW) ||
                hasPermission(PERMISSIONS.TEAM_VIEW)
              ),
              children: [
                {
                  key: 'users',
                  icon: <UserOutlined />,
                  label: <Link to="/admin/users">用户管理</Link>,
                  disabled: !hasPermission(PERMISSIONS.USER_VIEW),
                },
                {
                  key: 'roles',
                  icon: <SettingOutlined />,
                  label: <Link to="/admin/roles">角色管理</Link>,
                  disabled: !hasPermission(PERMISSIONS.ROLE_VIEW),
                },
                {
                  key: 'permissions',
                  icon: <SettingOutlined />,
                  label: <Link to="/admin/permissions">权限管理</Link>,
                  disabled: !hasPermission(PERMISSIONS.ROLE_VIEW),
                },
                {
                  key: 'teams',
                  icon: <TeamOutlined />,
                  label: <Link to="/admin/teams">团队管理</Link>,
                  disabled: !hasPermission(PERMISSIONS.TEAM_VIEW),
                },
              ],
            },
            {
              key: 'help',
              icon: <QuestionCircleOutlined />,
              label: <Link to="/help">使用帮助</Link>,
            },
          ]}
        />
      </Sider>
      <AntLayout style={{ marginLeft: collapsed ? 80 : 240, transition: 'all 0.2s' }}>
        <Header style={{ 
          padding: 0, 
          background: colorBgContainer, 
          position: 'sticky',
          top: 0,
          zIndex: 1,
          width: '100%',
          boxShadow: '0 1px 4px rgba(0, 21, 41, 0.08)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: 24 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: '16px', width: 64, height: 64 }}
            />
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <Title level={4} style={{ margin: 0, marginRight: 24 }}>台账管理系统</Title>
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                  <Avatar icon={<UserOutlined />} />
                  <span style={{ marginLeft: 8 }}>{user?.name || '用户'}</span>
                </div>
              </Dropdown>
            </div>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            minHeight: 280,
            overflow: 'initial',
            position: 'relative'
          }}
        >
          <Outlet />
        </Content>
        <Footer style={{ textAlign: 'center' }}>
          台账管理系统 ©{new Date().getFullYear()} 版权所有
        </Footer>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout; 