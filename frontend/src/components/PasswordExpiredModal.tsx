import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, message } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const PasswordExpiredModal: React.FC = () => {
  const { passwordExpired, changePassword, checkPasswordExpired } = useAuthStore();
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  
  useEffect(() => {
    // 登录后检查密码是否过期
    const checkPassword = async () => {
      const expired = await checkPasswordExpired();
      setVisible(expired);
    };
    
    checkPassword();
  }, [checkPasswordExpired]);
  
  useEffect(() => {
    setVisible(passwordExpired);
  }, [passwordExpired]);
  
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 检查两次输入的密码是否一致
      if (values.newPassword !== values.confirmPassword) {
        message.error('两次输入的密码不一致');
        return;
      }
      
      setLoading(true);
      const success = await changePassword(values.currentPassword, values.newPassword);
      
      if (success) {
        setVisible(false);
        form.resetFields();
      }
    } catch (error) {
      console.error('表单验证失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Modal
      title="密码已过期"
      open={visible}
      closable={false}
      maskClosable={false}
      keyboard={false}
      footer={[
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          修改密码
        </Button>
      ]}
    >
      <p>您的密码已超过90天未修改，为了账号安全，请立即修改密码。</p>
      
      <Form form={form} layout="vertical">
        <Form.Item
          name="currentPassword"
          label="当前密码"
          rules={[{ required: true, message: '请输入当前密码' }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" />
        </Form.Item>
        
        <Form.Item
          name="newPassword"
          label="新密码"
          rules={[
            { required: true, message: '请输入新密码' },
            { min: 8, message: '密码长度不能少于8个字符' }
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" />
        </Form.Item>
        
        <Form.Item
          name="confirmPassword"
          label="确认新密码"
          rules={[
            { required: true, message: '请确认新密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('newPassword') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('两次输入的密码不一致'));
              },
            }),
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请确认新密码" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default PasswordExpiredModal; 