import React, { useState } from 'react';
import { Form, Input, Button, Card, Tabs, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import api from '../api';

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
  
  // 如果已经登录，重定向到首页
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const onLoginFinish = async (values: LoginFormValues) => {
    const success = await login(values.username, values.password);
    if (success) {
      navigate('/');
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
    <div className="login-container">
      <Card className="login-card">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form
                  name="login"
                  initialValues={{ remember: true }}
                  onFinish={onLoginFinish}
                  size="large"
                  layout="vertical"
                  style={{ marginTop: 20 }}
                >
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: '请输入用户名!' }]}
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="用户名" 
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: '请输入密码!' }]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="密码"
                    />
                  </Form.Item>

                  <Form.Item>
                    <Button type="primary" htmlType="submit" block>
                      登录
                    </Button>
                  </Form.Item>
                </Form>
              )
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form
                  name="register"
                  onFinish={onRegisterFinish}
                  size="large"
                  layout="vertical"
                  style={{ marginTop: 20 }}
                >
                  <Form.Item
                    name="username"
                    rules={[
                      { required: true, message: '请输入用户名!' },
                      { min: 3, message: '用户名至少3个字符' }
                    ]}
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="用户名" 
                    />
                  </Form.Item>
                  <Form.Item
                    name="name"
                    rules={[{ required: true, message: '请输入姓名!' }]}
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="姓名" 
                    />
                  </Form.Item>
                  <Form.Item
                    name="ehr_id"
                    rules={[
                      { required: true, message: '请输入EHR号!' },
                      { min: 7, max: 7, message: 'EHR号必须是7位数字' },
                      { pattern: /^\d{7}$/, message: 'EHR号必须是7位数字' }
                    ]}
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="EHR号" 
                    />
                  </Form.Item>
                  <Form.Item
                    name="department"
                    rules={[{ required: true, message: '请输入部门!' }]}
                  >
                    <Input 
                      prefix={<UserOutlined />} 
                      placeholder="部门" 
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[
                      { required: true, message: '请输入密码!' },
                      { min: 6, message: '密码至少6个字符' }
                    ]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="密码"
                    />
                  </Form.Item>
                  <Form.Item
                    name="confirmPassword"
                    rules={[
                      { required: true, message: '请确认密码!' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('password') === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error('两次输入的密码不一致!'));
                        },
                      }),
                    ]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="确认密码"
                    />
                  </Form.Item>

                  <Form.Item>
                    <Button type="primary" htmlType="submit" block loading={registerLoading}>
                      注册
                    </Button>
                  </Form.Item>
                </Form>
              )
            }
          ]}
        />
      </Card>
    </div>
  );
};

export default LoginPage; 