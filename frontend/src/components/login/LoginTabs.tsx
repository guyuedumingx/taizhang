import React, { useState } from 'react';
import { Tabs, Typography } from 'antd';
import LoginForm, { LoginFormValues } from './LoginForm';
import RegisterForm, { RegisterFormValues } from './RegisterForm';

const { Text } = Typography;
const { TabPane } = Tabs;

interface LoginTabsProps {
  onLoginFinish: (values: LoginFormValues) => Promise<void>;
  onRegisterFinish: (values: RegisterFormValues) => Promise<void>;
  registerLoading: boolean;
}

const LoginTabs: React.FC<LoginTabsProps> = ({
  onLoginFinish,
  onRegisterFinish,
  registerLoading
}) => {
  const [activeTab, setActiveTab] = useState('login');

  return (
    <Tabs
      activeKey={activeTab}
      onChange={setActiveTab}
      className="login-tabs"
      centered
    >
      <TabPane tab="登录" key="login">
        <LoginForm onFinish={onLoginFinish} />
        <div className="form-actions">
          <a className="login-form-forgot" href="#!">
            忘记密码
          </a>
          <Text type="secondary">
            没有账号? <a onClick={() => setActiveTab('register')}>立即注册</a>
          </Text>
        </div>
      </TabPane>
      
      <TabPane tab="注册" key="register">
        <RegisterForm 
          onFinish={onRegisterFinish}
          loading={registerLoading}
        />
        <div className="form-actions">
          <Text type="secondary">
            已有账号? <a onClick={() => setActiveTab('login')}>立即登录</a>
          </Text>
        </div>
      </TabPane>
    </Tabs>
  );
};

export default LoginTabs; 