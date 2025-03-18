import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { message } from 'antd';
import api from '../api';

interface User {
  id: number;
  username: string;
  name: string;
  // role: string;
  roles: string[] | null;
  permissions: string[] | null;
  teamId?: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  passwordExpired: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  checkPasswordExpired: () => Promise<boolean>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>;
  updatePermissions: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: localStorage.getItem('auth-storage') ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token : null,
      isAuthenticated: !!localStorage.getItem('auth-storage') && !!JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token,
      passwordExpired: false,
      
      login: async (username: string, password: string) => {
        try {
          const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
              username,
              password,
            }),
          });
          
          if (!response.ok) {
            throw new Error('登录失败');
          }
          
          const data = await response.json();
          
          
          
          set({
            user: {
              id: data.user_id,
              username: data.username,
              name: data.name,
              // role: data.roles[0] || 'user',
              roles: data.roles,
              permissions: data.permissions || [],
              teamId: data.team_id,
            },
            token: data.access_token,
            isAuthenticated: true,
            passwordExpired: data.password_expired || false,
          });
          
          message.success('登录成功');
          return true;
        } catch (error) {
          // 显示错误消息
          console.error('登录失败:', error);
          message.error('登录失败，请检查用户名和密码');
          return false;
        }
      },
      
      logout: () => {
        // 清除本地存储
        localStorage.removeItem('auth-storage');
        
        // 重置状态
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          passwordExpired: false,
        });
      },
      
      hasPermission: (permission: string) => {
        const { user } = get();
        if (!user) return false;
        
        // 超级管理员拥有所有权限
        if (user.roles?.includes('admin')) return true;
        
        // 检查用户权限列表
        return user.permissions?.includes(permission) || user.permissions?.includes('*:*') || false;
      },
      
      checkPasswordExpired: async () => {
        if (!get().token) return false;
        
        try {
          const data = await api.auth.checkPasswordExpired();
          set({ passwordExpired: data.password_expired });
          return data.password_expired;
        } catch (error) {
          console.error('检查密码过期失败:', error);
          return false;
        }
      },
      
      changePassword: async (currentPassword, newPassword) => {
        if (!get().token) return false;
        
        try {
          await api.auth.changePassword(currentPassword, newPassword);
          set({ passwordExpired: false });
          message.success('密码修改成功');
          return true;
        } catch (error) {
          console.error('修改密码失败:', error);
          message.error('修改密码失败: ' + (error as Error).message);
          return false;
        }
      },
      
      updatePermissions: async () => {
        if (!get().token) return;
        
        try {
          const permissions = await api.users.getUserPermissions();
          set(state => ({
            user: state.user ? {
              ...state.user,
              permissions: permissions
            } : null
          }));
        } catch (error) {
          console.error('获取权限失败:', error);
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token, 
        isAuthenticated: state.isAuthenticated,
        passwordExpired: state.passwordExpired
      }),
    }
  )
); 