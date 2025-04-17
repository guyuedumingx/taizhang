import axios from 'axios';
import { API_BASE_URL } from '../config';
import {User, LoginResponse, RegisterRequest } from '../types';
// 从独立文件导入API
import * as WorkflowsAPI from './workflows';
import * as WorkflowNodesAPI from './workflow_nodes';
import * as WorkflowInstancesAPI from './workflow_instances';
import * as LedgersAPI from './ledgers';
import * as ApprovalsAPI from './approvals';
import * as LogsAPI from './logs';
import * as UsersAPI from './users';
import * as TeamsAPI from './teams';
import * as RolesAPI from './roles';
import * as TemplatesAPI from './templates';

// 导出所有API模块
export { 
  WorkflowsAPI,
  WorkflowNodesAPI, 
  WorkflowInstancesAPI,
  LedgersAPI,
  ApprovalsAPI,
  LogsAPI,
  UsersAPI,
  TeamsAPI,
  RolesAPI,
  TemplatesAPI
};

// 创建一个内存存储，用于测试环境
const tokenStorage = {
  token: null as string | null,
  setToken(token: string | null) {
    this.token = token;
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem('auth-storage', JSON.stringify({ state: { token } }));
      } else {
        localStorage.removeItem('auth-storage');
      }
    }
  },
  getToken() {
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem('auth-storage');
      return stored ? JSON.parse(stored).state?.token : null;
    }
    return this.token;
  },
  clear() {
    this.token = null;
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('auth-storage');
    }
  }
};

// 创建全局共享的axios实例
export const api = axios.create({
  baseURL: API_BASE_URL,
});

// 请求拦截器，添加token到请求头
api.interceptors.request.use(
  (config) => {
    const token = tokenStorage.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器，处理错误
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 处理401错误，清除token并跳转到登录页
    if (error.response && error.response.status === 401) {
      tokenStorage.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API客户端
export default {
  // 认证相关API
  auth: {
    // 登录
    login: async (username: string, password: string): Promise<LoginResponse> => {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await api.post<LoginResponse>('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      // 保存token
      if (response.data.access_token) {
        tokenStorage.setToken(response.data.access_token);
      }
      
      return response.data;
    },
    
    // 注册
    register: async (data: RegisterRequest): Promise<User> => {
      const response = await api.post<User>('/auth/register', data);
      return response.data;
    },
    
    // 获取当前用户信息
    me: async (): Promise<User> => {
      const response = await api.get('/auth/me');
      return response.data;
    },
    
    // 修改密码
    changePassword: async (old_password: string, new_password: string): Promise<{ message: string }> => {
      const response = await api.post('/auth/change-password', {
        old_password,
        new_password
      });
      return response.data;
    },
    
    // 检查密码是否过期
    checkPasswordExpired: async (): Promise<{ password_expired: boolean }> => {
      const response = await api.post('/auth/check-password-expired');
      return response.data;
    },
    
    // 登出
    logout: () => {
      tokenStorage.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  },
  
  // 此处保留对象导出，方便直接引用
  users: UsersAPI,
  teams: TeamsAPI,
  roles: RolesAPI,
  templates: TemplatesAPI,
  workflows: WorkflowsAPI,
  workflowNodes: WorkflowNodesAPI,
  workflowInstances: WorkflowInstancesAPI,
  ledgers: LedgersAPI,
  approvals: ApprovalsAPI,
  logs: LogsAPI
}; 