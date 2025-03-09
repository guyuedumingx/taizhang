import React, { useState } from 'react';
import { Form, Input, Button, Tabs, message, Typography, Divider } from 'antd';
import { UserOutlined, LockOutlined, IdcardOutlined, TeamOutlined, KeyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import api from '../api';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

// 中国银行Logo SVG - 简化版
const BOCLogo = () => (
  <svg width="120" height="40" viewBox="0 0 120 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22 6H98C106.837 6 114 13.1634 114 22V22C114 30.8366 106.837 38 98 38H22C13.1634 38 6 30.8366 6 22V22C6 13.1634 13.1634 6 22 6Z" fill="#D05A6E"/>
    <path d="M57 15H63C65.2091 15 67 16.7909 67 19V19C67 21.2091 65.2091 23 63 23H57C54.7909 23 53 21.2091 53 19V19C53 16.7909 54.7909 15 57 15Z" fill="white"/>
    <path d="M57 25H63C65.2091 25 67 26.7909 67 29V29C67 31.2091 65.2091 33 63 33H57C54.7909 33 53 31.2091 53 29V29C53 26.7909 54.7909 25 57 25Z" fill="white"/>
    <path d="M34 15L40 15C42.2091 15 44 16.7909 44 19V19C44 21.2091 42.2091 23 40 23H34C31.7909 23 30 21.2091 30 19V19C30 16.7909 31.7909 15 34 15Z" fill="white"/>
    <path d="M34 25H40C42.2091 25 44 26.7909 44 29V29C44 31.2091 42.2091 33 40 33H34C31.7909 33 30 31.2091 30 29V29C30 26.7909 31.7909 25 34 25Z" fill="white"/>
    <path d="M80 15H86C88.2091 15 90 16.7909 90 19V19C90 21.2091 88.2091 23 86 23H80C77.7909 23 76 21.2091 76 19V19C76 16.7909 77.7909 15 80 15Z" fill="white"/>
    <path d="M80 25H86C88.2091 25 90 26.7909 90 29V29C90 31.2091 88.2091 33 86 33H80C77.7909 33 76 31.2091 76 29V29C76 26.7909 77.7909 25 80 25Z" fill="white"/>
  </svg>
);

interface LoginFormValues {
  username: string;
  password: string;
}

interface RegisterFormValues {
  username: string;
  password: string;
  confirmPassword: string;
  ehr_id: string;
  name: string;
  department: string;
}

interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuthStore();
  const [activeTab, setActiveTab] = useState('login');
  const [registerLoading, setRegisterLoading] = useState(false);
  
  // 如果已经登录，重定向到仪表盘
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const onLoginFinish = async (values: LoginFormValues) => {
    const success = await login(values.username, values.password);
    if (success) {
      navigate('/dashboard');
    }
  };

  const onRegisterFinish = async (values: RegisterFormValues) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次输入的密码不一致');
      return;
    }

    setRegisterLoading(true);
    try {
      // 调用注册API
      await api.auth.register({
        username: values.username,
        password: values.password,
        ehr_id: values.ehr_id,
        name: values.name,
        department: values.department
      });
      
      message.success('注册成功，请登录');
      setActiveTab('login');
    } catch (error) {
      const apiError = error as ApiError;
      if (apiError.response?.data?.detail) {
        message.error(apiError.response.data.detail);
      } else {
        message.error('注册失败，请稍后再试');
      }
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-left-content">
          <div className="login-branding">
            <BOCLogo />
            <Title level={2} className="bank-name">中国银行</Title>
          </div>
          <div className="login-intro">
            <Title level={3}>台账管理系统</Title>
            <Paragraph className="subtitle">集约运营中心（广东）</Paragraph>
            <Paragraph className="description">
              高效、安全的台账管理平台，为您提供专业的数据管理与分析服务。
            </Paragraph>
          </div>
          <div className="login-features">
            <div className="feature-item">
              <div className="feature-icon secure"></div>
              <div className="feature-text">
                <Text strong>安全可靠</Text>
                <Text type="secondary">多重加密保障数据安全</Text>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon efficient"></div>
              <div className="feature-text">
                <Text strong>高效便捷</Text>
                <Text type="secondary">简化工作流程，提高效率</Text>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon professional"></div>
              <div className="feature-text">
                <Text strong>专业服务</Text>
                <Text type="secondary">提供全方位数据管理服务</Text>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="login-right">
        <div className="login-form-container">
          <div className="form-header">
            <Title level={4}>欢迎使用</Title>
            <Text type="secondary">请登录您的账号以继续</Text>
          </div>
          
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            centered
            className="login-tabs"
          >
            <TabPane tab="登录" key="login">
              <Form
                name="login"
                layout="vertical"
                onFinish={onLoginFinish}
                size="large"
                className="login-form"
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input 
                    prefix={<UserOutlined className="site-form-item-icon" />} 
                    placeholder="用户名"
                    autoComplete="username"
                  />
                </Form.Item>
                
                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input.Password 
                    prefix={<LockOutlined className="site-form-item-icon" />} 
                    placeholder="密码"
                    autoComplete="current-password"
                  />
                </Form.Item>
                
                <Form.Item className="form-button">
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    block
                    size="large"
                  >
                    登录
                  </Button>
                </Form.Item>
                
                <div className="form-actions">
                  <a className="login-form-forgot" href="#!">
                    忘记密码
                  </a>
                  <Text type="secondary">
                    没有账号? <a onClick={() => setActiveTab('register')}>立即注册</a>
                  </Text>
                </div>
              </Form>
            </TabPane>
            
            <TabPane tab="注册" key="register">
              <Form
                name="register"
                layout="vertical"
                onFinish={onRegisterFinish}
                size="large"
                className="login-form"
              >
                <Form.Item
                  name="username"
                  rules={[
                    { required: true, message: '请输入用户名' },
                    { min: 3, message: '用户名至少3个字符' }
                  ]}
                >
                  <Input 
                    prefix={<UserOutlined className="site-form-item-icon" />} 
                    placeholder="用户名"
                    autoComplete="username"
                  />
                </Form.Item>
                
                <Form.Item
                  name="name"
                  rules={[{ required: true, message: '请输入真实姓名' }]}
                >
                  <Input 
                    prefix={<UserOutlined className="site-form-item-icon" />} 
                    placeholder="真实姓名"
                    autoComplete="name"
                  />
                </Form.Item>
                
                <div className="form-row">
                  <Form.Item
                    name="ehr_id"
                    rules={[
                      { required: true, message: '请输入EHR号' },
                      { min: 7, max: 7, message: 'EHR号必须是7位数字' },
                      { pattern: /^\d{7}$/, message: 'EHR号必须是7位数字' }
                    ]}
                    className="form-col"
                  >
                    <Input 
                      prefix={<IdcardOutlined className="site-form-item-icon" />} 
                      placeholder="EHR号"
                    />
                  </Form.Item>
                  
                  <Form.Item
                    name="department"
                    rules={[{ required: true, message: '请输入部门' }]}
                    className="form-col"
                  >
                    <Input 
                      prefix={<TeamOutlined className="site-form-item-icon" />} 
                      placeholder="部门"
                    />
                  </Form.Item>
                </div>
                
                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { min: 6, message: '密码至少6个字符' }
                  ]}
                >
                  <Input.Password 
                    prefix={<LockOutlined className="site-form-item-icon" />} 
                    placeholder="密码"
                    autoComplete="new-password"
                  />
                </Form.Item>
                
                <Form.Item
                  name="confirmPassword"
                  rules={[
                    { required: true, message: '请确认密码' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('两次输入的密码不一致'));
                      },
                    }),
                  ]}
                >
                  <Input.Password 
                    prefix={<KeyOutlined className="site-form-item-icon" />} 
                    placeholder="确认密码"
                    autoComplete="new-password"
                  />
                </Form.Item>
                
                <Form.Item className="form-button">
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    block
                    size="large"
                    loading={registerLoading}
                  >
                    注册
                  </Button>
                </Form.Item>
                
                <div className="form-actions">
                  <Text type="secondary">
                    已有账号? <a onClick={() => setActiveTab('login')}>立即登录</a>
                  </Text>
                </div>
              </Form>
            </TabPane>
          </Tabs>
          
          <Divider plain>
            <Text type="secondary">安全登录提示</Text>
          </Divider>
          
          <Paragraph className="security-tips" type="secondary">
            为了保障您的账号安全，请不要共享密码，登录后请及时退出。
          </Paragraph>
        </div>
        
        <div className="login-footer">
          <Text type="secondary">© {new Date().getFullYear()} 中国银行集约运营中心（广东）台账管理系统</Text>
          <div className="footer-links">
            <a href="#!">使用条款</a>
            <a href="#!">隐私政策</a>
            <a href="#!">帮助中心</a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage; 