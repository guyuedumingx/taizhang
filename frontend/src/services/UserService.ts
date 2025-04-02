import api from '../api';
import { User, UserCreate, UserUpdate } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class UserService {
  // 获取用户列表
  static async getUsers(params?: QueryParams): Promise<User[]> {
    try {
      const response = await api.users.getUsers(params);
      console.log('Users API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取users数组');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error('API返回的users格式不正确:', response);
      return [];
    } catch (error) {
      console.error('获取用户列表失败:', error);
      throw error;
    }
  }

  // 获取用户详情
  static async getUser(id: number): Promise<User> {
    try {
      const response = await api.users.getUser(id);
      console.log(`获取用户 ${id} 详情返回数据:`, response);
      
      // 如果返回的是对象，并且有可能包含用户数据
      if (response && typeof response === 'object') {
        // 处理可能的嵌套数据
        if ('item' in response && response.item) {
          console.log(`从嵌套数据中提取用户详情`);
          return response.item as User;
        }
        
        // 如果有id字段，可能就是用户对象本身
        if ('id' in response) {
          return response as User;
        }
      }
      
      console.error(`获取用户 ${id} 详情返回格式不正确:`, response);
      throw new Error(`无法解析用户数据`);
    } catch (error) {
      console.error(`获取用户 ${id} 详情失败:`, error);
      throw error;
    }
  }

  // 创建用户
  static async createUser(data: UserCreate): Promise<User> {
    try {
      return await api.users.createUser(data);
    } catch (error) {
      console.error('创建用户失败:', error);
      throw error;
    }
  }

  // 更新用户
  static async updateUser(id: number, data: UserUpdate): Promise<User> {
    try {
      return await api.users.updateUser(id, data);
    } catch (error) {
      console.error(`更新用户 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除用户
  static async deleteUser(id: number): Promise<void> {
    try {
      await api.users.deleteUser(id);
    } catch (error) {
      console.error(`删除用户 ${id} 失败:`, error);
      throw error;
    }
  }

  // 批量导入用户
  static async importUsers(file: File): Promise<{
    success_count: number;
    failed_count: number;
    failed_users: Array<{
      row: number;
      username: string;
      reason: string;
    }>;
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('未授权，请先登录');
      }
      
      const response = await fetch('/api/v1/users/import', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || '导入失败');
      }
      
      return result;
    } catch (error) {
      console.error('导入用户失败:', error);
      throw error;
    }
  }

  // 获取当前用户信息
  static async getCurrentUser(): Promise<User> {
    try {
      return await api.auth.me();
    } catch (error) {
      console.error('获取当前用户信息失败:', error);
      throw error;
    }
  }
} 