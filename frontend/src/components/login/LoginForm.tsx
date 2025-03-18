import React from 'react';
import { Form, Input, Button } from 'antd';
import { IdcardOutlined, LockOutlined } from '@ant-design/icons';

export interface LoginFormValues {
  username: string;  // 实际上是EHR号
  password: string;
}

interface LoginFormProps {
  onFinish: (values: LoginFormValues) => Promise<void>;
  loading?: boolean;
}

const LoginForm: React.FC<LoginFormProps> = ({ onFinish, loading = false }) => {
  return (
    <Form
      name="login-form"
      className="login-form"
      initialValues={{ remember: true }}
      onFinish={onFinish}
    >
      <Form.Item
        name="username"
        rules={[
          { required: true, message: '请输入EHR号' },
          { pattern: /^\d{7}$/, message: 'EHR号必须是7位数字' }
        ]}
      >
        <Input 
          prefix={<IdcardOutlined className="site-form-item-icon" />} 
          placeholder="EHR号" 
          size="large"
        />
      </Form.Item>
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
          size="large"
        />
      </Form.Item>

      <Form.Item className="form-button">
        <Button 
          type="primary" 
          htmlType="submit" 
          className="login-form-button" 
          block
          size="large"
          loading={loading}
        >
          登录
        </Button>
      </Form.Item>
    </Form>
  );
};

export default LoginForm; 