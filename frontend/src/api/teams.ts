import { api } from './index';
import { Team, TeamCreate, TeamUpdate, User } from '../types';
import { QueryParams, buildQueryParams } from './util';

// 获取团队列表
export async function getTeams(params?: QueryParams): Promise<Team[]> {
  const query = buildQueryParams(params);
  const response = await api.get(`/teams/${query}`);
  return response.data;
}

// 获取团队详情
export async function getTeam(id: number): Promise<Team> {
  const response = await api.get(`/teams/${id}`);
  return response.data;
}

// 创建团队
export async function createTeam(data: TeamCreate): Promise<Team> {
  const response = await api.post('/teams/', data);
  return response.data;
}

// 更新团队
export async function updateTeam(id: number, data: TeamUpdate): Promise<Team> {
  const response = await api.put(`/teams/${id}`, data);
  return response.data;
}

// 删除团队
export async function deleteTeam(id: number): Promise<Team> {
  const response = await api.delete(`/teams/${id}`);
  return response.data;
}

// 获取团队成员
export async function getTeamMembers(id: number): Promise<User[]> {
  const response = await api.get(`/teams/${id}/members`);
  return response.data;
} 