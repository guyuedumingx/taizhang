import api from '../api';
import { Role, RoleCreate, RoleUpdate } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class RoleService {
  // 获取角色列表
  static async getRoles(params?: QueryParams): Promise<Role[]> {
    try {
      return await api.roles.getRoles(params);
    } catch (error) {
      console.error('获取角色列表失败:', error);
      throw error;
    }
  }

  // 获取角色详情
  static async getRole(id: number): Promise<Role> {
    try {
      return await api.roles.getRole(id);
    } catch (error) {
      console.error(`获取角色 ${id} 详情失败:`, error);
      throw error;
    }
  }

  // 创建角色
  static async createRole(data: RoleCreate): Promise<Role> {
    try {
      return await api.roles.createRole(data);
    } catch (error) {
      console.error('创建角色失败:', error);
      throw error;
    }
  }

  // 更新角色
  static async updateRole(id: number, data: RoleUpdate): Promise<Role> {
    try {
      return await api.roles.updateRole(id, data);
    } catch (error) {
      console.error(`更新角色 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除角色
  static async deleteRole(id: number): Promise<void> {
    try {
      await api.roles.deleteRole(id);
    } catch (error) {
      console.error(`删除角色 ${id} 失败:`, error);
      throw error;
    }
  }

  // 获取用户角色
  static async getUserRoles(userId: number): Promise<string[]> {
    try {
      return await api.roles.getUserRoles(userId);
    } catch (error) {
      console.error(`获取用户 ${userId} 的角色失败:`, error);
      throw error;
    }
  }

  // 添加用户角色
  static async addUserRole(userId: number, roleName: string): Promise<{ message: string }> {
    try {
      return await api.roles.addUserRole(userId, roleName);
    } catch (error) {
      console.error(`为用户 ${userId} 添加角色失败:`, error);
      throw error;
    }
  }

  // 删除用户角色
  static async removeUserRole(userId: number, roleName: string): Promise<{ message: string }> {
    try {
      return await api.roles.removeUserRole(userId, roleName);
    } catch (error) {
      console.error(`为用户 ${userId} 删除角色失败:`, error);
      throw error;
    }
  }
} 