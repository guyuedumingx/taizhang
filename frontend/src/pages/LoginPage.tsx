import React, { useState, useEffect } from 'react';
import { message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import api from '../api';
import { 
  LoginPageLayout, 
  LoginTabs, 
  SecurityTips 
} from '../components/login';
import type { LoginFormValues } from '../components/login/LoginForm';
import type { RegisterFormValues } from '../components/login/RegisterForm';

interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, updatePermissions, checkPasswordExpired } = useAuthStore();
  const [registerLoading, setRegisterLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const onLoginFinish = async (values: LoginFormValues) => {
    const success = await login(values.username, values.password);
    if (success) {
      // 登录成功后更新权限信息
      await updatePermissions();
      
      // 检查密码是否过期
      const passwordExpired = await checkPasswordExpired();
      
      // 如果密码过期，跳转到修改密码页面
      if (passwordExpired) {
        navigate('/change-password');
      } else {
        // 否则跳转到首页
        navigate('/dashboard');
      }
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
    <LoginPageLayout>
      <div className="login-form-container">
        <div className="form-header">
          <h4>欢迎使用台账管理系统</h4>
        </div>
        
        <LoginTabs 
          onLoginFinish={onLoginFinish}
          onRegisterFinish={onRegisterFinish}
          registerLoading={registerLoading}
        />
        
        <SecurityTips />
      </div>
    </LoginPageLayout>
  );
};

export default LoginPage; 