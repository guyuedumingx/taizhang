import { api } from './index';
import { Role, RoleCreate, RoleUpdate } from '../types';
import { QueryParams, buildQueryParams } from './util';

// 获取角色列表
export async function getRoles(params?: QueryParams): Promise<Role[]> {
  const query = buildQueryParams(params);
  const response = await api.get(`/roles/${query}`);
  return response.data;
}

// 获取角色详情
export async function getRole(id: number): Promise<Role> {
  const response = await api.get(`/roles/${id}`);
  return response.data;
}

// 创建角色
export async function createRole(data: RoleCreate): Promise<Role> {
  const response = await api.post('/roles/', data);
  return response.data;
}

// 更新角色
export async function updateRole(id: number, data: RoleUpdate): Promise<Role> {
  const response = await api.put(`/roles/${id}`, data);
  return response.data;
}

// 删除角色
export async function deleteRole(id: number): Promise<Role> {
  const response = await api.delete(`/roles/${id}`);
  return response.data;
}

// 获取用户角色
export async function getUserRoles(userId: number): Promise<string[]> {
  const response = await api.get(`/roles/user/${userId}/roles`);
  return response.data;
}

// 添加用户角色
export async function addUserRole(userId: number, roleName: string): Promise<{ message: string }> {
  const response = await api.post(`/roles/user/${userId}/roles/${roleName}`);
  return response.data;
}

// 删除用户角色
export async function removeUserRole(userId: number, roleName: string): Promise<{ message: string }> {
  const response = await api.delete(`/roles/user/${userId}/roles/${roleName}`);
  return response.data;
} 