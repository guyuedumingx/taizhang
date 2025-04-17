import { api } from './index';
import { User, UserCreate, UserUpdate } from '../types';
import { QueryParams, buildQueryParams } from './util';

// 获取用户列表
export async function getUsers(params?: QueryParams): Promise<User[]> {
  const query = buildQueryParams(params);
  const response = await api.get(`/users/${query}`);
  return response.data;
}

// 获取用户详情
export async function getUser(id: number): Promise<User> {
  const response = await api.get(`/users/${id}`);
  return response.data; 
}

// 获取当前用户权限
export async function getUserPermissions(): Promise<string[]> {
  const response = await api.get('/users/me/permissions');
  return response.data;
}

// 创建用户
export async function createUser(data: UserCreate): Promise<User> {
  const response = await api.post('/users/', data);
  return response.data;
}

// 更新用户
export async function updateUser(id: number, data: UserUpdate): Promise<User> {
  const response = await api.put(`/users/${id}`, data);
  return response.data;
}

// 删除用户
export async function deleteUser(id: number): Promise<User> {
  const response = await api.delete(`/users/${id}`);
  return response.data;
}

// 批量导入用户
export async function importUsers(file: File): Promise<{
  success_count: number;
  failed_count: number;
  failed_users: Array<{
    row: number;
    username: string;
    reason: string;
  }>;
}> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/users/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
} 