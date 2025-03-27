import api from '../api';
import { Team, TeamCreate, TeamUpdate, User } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class TeamService {
  // 获取团队列表
  static async getTeams(params?: QueryParams): Promise<Team[]> {
    try {
      const response = await api.teams.getTeams(params);
      console.log('Teams API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取teams数组:', response.items);
        
        // 从分页数据中提取items数组并处理leader_id
        return response.items.map(team => ({
          ...team,
          leader_id: team.leader_id !== null ? Number(team.leader_id) : null
        }));
      }
      
      // 如果返回的是数组，直接处理
      if (Array.isArray(response)) {
        return response.map(team => ({
          ...team,
          leader_id: team.leader_id !== null ? Number(team.leader_id) : null
        }));
      }
      
      // 其他情况返回空数组
      console.error('API返回的teams格式不正确:', response);
      return [];
    } catch (error) {
      console.error('获取团队列表失败:', error);
      throw error;
    }
  }

  // 获取团队详情
  static async getTeam(id: number): Promise<Team> {
    try {
      const team = await api.teams.getTeam(id);
      
      // 确保返回的team数据中leader_id字段是正确的类型
      return {
        ...team,
        leader_id: team.leader_id !== null ? Number(team.leader_id) : null
      };
    } catch (error) {
      console.error(`获取团队 ${id} 详情失败:`, error);
      throw error;
    }
  }

  // 创建团队
  static async createTeam(data: TeamCreate): Promise<Team> {
    try {
      // 确保创建团队时leader_id是正确的类型
      const createData = {
        ...data,
        leader_id: data.leader_id !== undefined ? Number(data.leader_id) : null
      } as TeamCreate;
      
      return await api.teams.createTeam(createData);
    } catch (error) {
      console.error('创建团队失败:', error);
      throw error;
    }
  }

  // 更新团队
  static async updateTeam(id: number, data: TeamUpdate): Promise<Team> {
    try {
      // 确保更新团队时leader_id是正确的类型
      const updateData = {
        ...data,
        leader_id: data.leader_id !== undefined ? Number(data.leader_id) : undefined
      };
      
      return await api.teams.updateTeam(id, updateData);
    } catch (error) {
      console.error(`更新团队 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除团队
  static async deleteTeam(id: number): Promise<void> {
    try {
      await api.teams.deleteTeam(id);
    } catch (error) {
      console.error(`删除团队 ${id} 失败:`, error);
      throw error;
    }
  }

  // 获取团队成员
  static async getTeamMembers(id: number): Promise<User[]> {
    try {
      const response = await api.teams.getTeamMembers(id);
      console.log(`获取团队 ${id} 成员返回数据:`, response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log(`从分页数据中提取团队 ${id} 成员数组`);
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error(`获取团队 ${id} 成员返回格式不正确:`, response);
      return [];
    } catch (error) {
      console.error(`获取团队 ${id} 成员失败:`, error);
      throw error;
    }
  }

  // 获取用户列表
  static async getUsers(): Promise<User[]> {
    try {
      const response = await api.users.getUsers();
      console.log('Users API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取users数组，共 ' + response.items.length + ' 条数据');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        console.log('用户数据已是数组格式，共 ' + response.length + ' 条数据');
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
} 