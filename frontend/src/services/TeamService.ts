import api from '../api';
import { Team, TeamCreate, TeamUpdate, User } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class TeamService {
  // 获取团队列表
  static async getTeams(params?: QueryParams): Promise<Team[]> {
    try {
      const teams = await api.teams.getTeams(params);
      
      // 确保返回的teams数据中leader_id字段是正确的类型
      return teams.map(team => ({
        ...team,
        leader_id: team.leader_id !== null ? Number(team.leader_id) : null
      }));
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
        leader_id: data.leader_id !== undefined ? Number(data.leader_id) : undefined
      };
      
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
      return await api.teams.getTeamMembers(id);
    } catch (error) {
      console.error(`获取团队 ${id} 成员失败:`, error);
      throw error;
    }
  }

  // 获取用户列表
  static async getUsers(): Promise<User[]> {
    try {
      return await api.users.getUsers();
    } catch (error) {
      console.error('获取用户列表失败:', error);
      throw error;
    }
  }
} 