import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { message } from 'antd';
import { authApi } from '../api';

interface User {
  id: number;
  username: string;
  name: string;
  role: string;
  permissions: string[];
  teamId?: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: async (username: string, password: string) => {
        try {
          const response = await authApi.login(username, password);
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
          });
          message.success('登录成功');
          return true;
        } catch (/* eslint-disable-next-line @typescript-eslint/no-unused-vars */error) {
          // 忽略错误对象，只显示错误消息
          message.error('登录失败，请检查用户名和密码');
          return false;
        }
      },
      
      logout: async () => {
        try {
          await authApi.logout();
        } finally {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          });
          message.success('已退出登录');
        }
      },
      
      hasPermission: (permission: string) => {
        const { user } = get();
        if (!user) return false;
        
        // 超级管理员拥有所有权限
        if (user.permissions.includes('*:*')) return true;
        
        return user.permissions.includes(permission);
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
); 