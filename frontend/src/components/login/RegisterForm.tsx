import React from 'react';
import { Form, Input, Button } from 'antd';
import { UserOutlined, LockOutlined, IdcardOutlined, TeamOutlined, KeyOutlined } from '@ant-design/icons';

export interface RegisterFormValues {
  username: string;
  password: string;
  confirmPassword: string;
  ehr_id: string;
  name: string;
  department: string;
}

interface RegisterFormProps {
  onFinish: (values: RegisterFormValues) => Promise<void>;
  loading: boolean;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onFinish, loading }) => {
  return (
    <Form
      name="register"
      layout="vertical"
      onFinish={onFinish}
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
          loading={loading}
        >
          注册
        </Button>
      </Form.Item>
    </Form>
  );
};

export default RegisterForm; 