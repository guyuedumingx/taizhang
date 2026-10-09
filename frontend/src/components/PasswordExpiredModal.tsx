import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, message } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const PasswordExpiredModal: React.FC = () => {
  const { passwordExpired, isFirstLogin, changePassword, checkPasswordExpired, isAuthenticated, token } = useAuthStore();
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    // 登录后检查密码是否过期
    const checkPassword = async () => {
      if (!isAuthenticated || !token) return;
      const expired = await checkPasswordExpired();
      setVisible(expired);
    };

    checkPassword();
  }, [checkPasswordExpired, isAuthenticated, token]);

  useEffect(() => {
    // PRD §3.2: passwordExpired 或 isFirstLogin 任一为 true 都强制弹窗
    setVisible(passwordExpired || isFirstLogin);
  }, [passwordExpired, isFirstLogin]);

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

  // PRD §3.2: 首次登录时去掉"当前密码"项, 因为可能没有"旧密码"概念
  const isFirstLoginMode = isFirstLogin && !passwordExpired;
  const modalTitle = isFirstLoginMode ? '首次登录 - 请修改密码' : '密码已过期';
  const promptText = isFirstLoginMode
    ? '检测到您是首次登录, 为了账号安全, 请立即设置新密码。'
    : '您的密码已超过90天未修改, 为了账号安全, 请立即修改密码。';

  return (
    <Modal
      title={modalTitle}
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
      <p>{promptText}</p>

      <Form form={form} layout="vertical">
        {!isFirstLoginMode && (
          <Form.Item
            name="currentPassword"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" />
          </Form.Item>
        )}

        <Form.Item
          name="newPassword"
          label="新密码"
          rules={[
            { required: true, message: '请输入新密码' },
            { min: 6, message: '密码至少6位数字' },
            { pattern: /^\d+$/, message: '密码必须是数字' },
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="请输入6位数字密码" />
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