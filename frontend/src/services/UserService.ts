import api from '../api';
import { User, UserCreate, UserUpdate } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class UserService {
  // 获取用户列表
  static async getUsers(params?: QueryParams): Promise<User[]> {
    try {
      return await api.users.getUsers(params);
    } catch (error) {
      console.error('获取用户列表失败:', error);
      throw error;
    }
  }

  // 获取用户详情
  static async getUser(id: number): Promise<User> {
    try {
      return await api.users.getUser(id);
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