import axios from 'axios';
import { API_BASE_URL } from '../config';
import {
  User, UserCreate, UserUpdate,
  Team, TeamCreate, TeamUpdate,
  Role, RoleCreate, RoleUpdate,
  Template, TemplateDetail, TemplateCreate, TemplateUpdate,
  Field, FieldCreate, FieldUpdate,
  LoginResponse, RegisterRequest
} from '../types';

// 从独立文件导入API
import * as WorkflowsAPI from './workflows';
import * as WorkflowNodesAPI from './workflow_nodes';
import * as WorkflowInstancesAPI from './workflow_instances';
import * as LedgersAPI from './ledgers';
import * as ApprovalsAPI from './approvals';
import * as LogsAPI from './logs';

// 导出所有API模块
export { 
  WorkflowsAPI,
  WorkflowNodesAPI, 
  WorkflowInstancesAPI,
  LedgersAPI,
  ApprovalsAPI,
  LogsAPI
};

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

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

const api = axios.create({
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

// 构建查询参数
const buildQueryParams = (params?: QueryParams): string => {
  if (!params) return '';
  
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
    .join('&');
  
  return query ? `?${query}` : '';
};

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
  
  // 用户管理API
  users: {
    // 获取用户列表
    getUsers: async (params?: QueryParams): Promise<User[]> => {
      const query = buildQueryParams(params);
      const response = await api.get(`/users/${query}`);
      return response.data;
    },
    
    // 获取用户详情
    getUser: async (id: number): Promise<User> => {
      const response = await api.get(`/users/${id}`);
      return response.data; 
    },
    
    // 获取当前用户权限
    getUserPermissions: async (): Promise<string[]> => {
      const response = await api.get('/users/me/permissions');
      return response.data;
    },
    
    // 创建用户
    createUser: async (data: UserCreate): Promise<User> => {
      const response = await api.post('/users/', data);
      return response.data;
    },
    
    // 更新用户
    updateUser: async (id: number, data: UserUpdate): Promise<User> => {
      const response = await api.put(`/users/${id}`, data);
      return response.data;
    },
    
    // 删除用户
    deleteUser: async (id: number): Promise<User> => {
      const response = await api.delete(`/users/${id}`);
      return response.data;
    }
  },
  
  // 团队管理API
  teams: {
    // 获取团队列表
    getTeams: async (params?: QueryParams): Promise<Team[]> => {
      const query = buildQueryParams(params);
      const response = await api.get(`/teams/${query}`);
      return response.data;
    },
    
    // 获取团队详情
    getTeam: async (id: number): Promise<Team> => {
      const response = await api.get(`/teams/${id}`);
      return response.data;
    },
    
    // 创建团队
    createTeam: async (data: TeamCreate): Promise<Team> => {
      const response = await api.post('/teams/', data);
      return response.data;
    },
    
    // 更新团队
    updateTeam: async (id: number, data: TeamUpdate): Promise<Team> => {
      const response = await api.put(`/teams/${id}`, data);
      return response.data;
    },
    
    // 删除团队
    deleteTeam: async (id: number): Promise<Team> => {
      const response = await api.delete(`/teams/${id}`);
      return response.data;
    },
    
    // 获取团队成员
    getTeamMembers: async (id: number): Promise<User[]> => {
      const response = await api.get(`/teams/${id}/members`);
      return response.data;
    }
  },
  
  // 角色管理API
  roles: {
    // 获取角色列表
    getRoles: async (params?: QueryParams): Promise<Role[]> => {
      const query = buildQueryParams(params);
      const response = await api.get(`/roles/${query}`);
      return response.data;
    },
    
    // 获取角色详情
    getRole: async (id: number): Promise<Role> => {
      const response = await api.get(`/roles/${id}`);
      return response.data;
    },
    
    // 创建角色
    createRole: async (data: RoleCreate): Promise<Role> => {
      const response = await api.post('/roles/', data);
      return response.data;
    },
    
    // 更新角色
    updateRole: async (id: number, data: RoleUpdate): Promise<Role> => {
      const response = await api.put(`/roles/${id}`, data);
      return response.data;
    },
    
    // 删除角色
    deleteRole: async (id: number): Promise<Role> => {
      const response = await api.delete(`/roles/${id}`);
      return response.data;
    },
    
    // 获取用户角色
    getUserRoles: async (userId: number): Promise<string[]> => {
      const response = await api.get(`/roles/user/${userId}/roles`);
      return response.data;
    },
    
    // 添加用户角色
    addUserRole: async (userId: number, roleName: string): Promise<{ message: string }> => {
      const response = await api.post(`/roles/user/${userId}/roles/${roleName}`);
      return response.data;
    },
    
    // 删除用户角色
    removeUserRole: async (userId: number, roleName: string): Promise<{ message: string }> => {
      const response = await api.delete(`/roles/user/${userId}/roles/${roleName}`);
      return response.data;
    }
  },
  
  // 模板管理API
  templates: {
    // 获取模板列表
    getTemplates: async (params?: QueryParams): Promise<Template[]> => {
      const query = buildQueryParams(params);
      const response = await api.get(`/templates/${query}`);
      return response.data;
    },
    
    // 获取模板详情
    getTemplate: async (id: number): Promise<Template> => {
      const response = await api.get(`/templates/${id}`);
      return response.data;
    },
    
    // 获取模板详情（包含字段）
    getTemplateDetail: async (id: number): Promise<TemplateDetail> => {
      const response = await api.get(`/templates/${id}`);
      return response.data;
    },
    
    // 创建模板
    createTemplate: async (data: TemplateCreate): Promise<Template> => {
      const response = await api.post('/templates/', data);
      return response.data;
    },
    
    // 更新模板
    updateTemplate: async (id: number, data: TemplateUpdate): Promise<Template> => {
      const response = await api.put(`/templates/${id}`, data);
      return response.data;
    },
    
    // 删除模板
    deleteTemplate: async (id: number): Promise<Template> => {
      const response = await api.delete(`/templates/${id}`);
      return response.data;
    },
    
    // 获取模板字段
    getTemplateFields: async (id: number): Promise<Field[]> => {
      const response = await api.get(`/templates/${id}/fields`);
      return response.data;
    },
    
    // 创建模板字段
    createField: async (templateId: number, data: FieldCreate): Promise<Field> => {
      const response = await api.post(`/templates/${templateId}/fields`, data);
      return response.data;
    },
    
    // 更新模板字段
    updateField: async (templateId: number, fieldId: number, data: FieldUpdate): Promise<Field> => {
      const response = await api.put(`/templates/${templateId}/fields/${fieldId}`, data);
      return response.data;
    },
    
    // 删除模板字段
    deleteField: async (templateId: number, fieldId: number): Promise<Field> => {
      const response = await api.delete(`/templates/${templateId}/fields/${fieldId}`);
      return response.data;
    }
  }
}; 