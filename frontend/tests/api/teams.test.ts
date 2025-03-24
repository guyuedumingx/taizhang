import { describe, it, expect, beforeAll } from 'vitest'
import axios from 'axios'
import { API_BASE_URL } from '../../src/config'
import { LoginResponse, Team, User } from '../../src/types'

// 创建一个测试专用的 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
})

// 创建表单数据的辅助函数
function createFormData(ehr_id: string, password: string): URLSearchParams {
  const params = new URLSearchParams()
  params.append('username', ehr_id)  // OAuth2 要求使用 username 字段
  params.append('password', password)
  return params
}

describe('团队管理 API 测试', () => {
  let authToken: string
  let testTeamId: number
  let testUserId: number

  // 在所有测试开始前登录获取 token 并创建测试用户
  beforeAll(async () => {
    // 登录获取 token
    const formData = new URLSearchParams()
    formData.append('username', '1234567')  // EHR ID作为username
    formData.append('password', 'password123')
    
    const loginResponse = await api.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
    authToken = loginResponse.data.access_token
    api.defaults.headers.common['Authorization'] = `Bearer ${authToken}`

    // 创建测试用户
    const timestamp = Date.now().toString().slice(-7)  // 取后7位作为EHR ID
    const newUser = {
      username: `test_user_${timestamp}`,
      ehr_id: timestamp,  // 7位数字
      password: 'password123',
      name: '测试用户',
      department: '测试部门',
      is_active: true,
      roles: ['admin', 'user']  // 添加admin角色以获取管理权限
    }
    const userResponse = await api.post<User>('/users/', newUser)
    testUserId = userResponse.data.id
  })

  // 测试获取团队列表
  it('应该能获取团队列表', async () => {
    const response = await api.get('/teams/')
    
    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('items')
    expect(Array.isArray(response.data.items)).toBe(true)
  })

  // 测试创建团队
  it('应该能创建新团队', async () => {
    const newTeam = {
      name: `测试团队${Date.now()}`,
      description: '这是一个测试团队',
      department: '测试部门'
    }

    const response = await api.post<Team>('/teams/', newTeam)
    
    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('id')
    expect(response.data.name).toBe(newTeam.name)
    expect(response.data.description).toBe(newTeam.description)
    
    testTeamId = response.data.id
  })

  // 测试获取单个团队
  it('应该能获取指定团队', async () => {
    const response = await api.get<Team>(`/teams/${testTeamId}`)
    
    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('id', testTeamId)
  })

  // 测试更新团队
  it('应该能更新团队信息', async () => {
    const updateData = {
      name: '更新后的团队名称',
      description: '更新后的团队描述',
      department: '更新后的部门'
    }

    const response = await api.put<Team>(`/teams/${testTeamId}`, updateData)
    
    expect(response.status).toBe(200)
    expect(response.data.name).toBe(updateData.name)
    expect(response.data.description).toBe(updateData.description)
  })

  // 测试添加团队成员
  it('应该能添加团队成员', async () => {
    const response = await api.post(`/teams/${testTeamId}/members/${testUserId}`)
    expect(response.status).toBe(204)
  })

  // 测试移除团队成员
  it('应该能移除团队成员', async () => {
    const response = await api.delete(`/teams/${testTeamId}/members/${testUserId}`)
    expect(response.status).toBe(204)
  })

  // 测试删除团队
  it('应该能删除团队', async () => {
    const response = await api.delete(`/teams/${testTeamId}`)
    expect(response.status).toBe(204)

    // 验证团队已被删除
    try {
      await api.get<Team>(`/teams/${testTeamId}`)
    } catch (error) {
      if (axios.isAxiosError(error)) {
        expect(error.response?.status).toBe(404)
      } else {
        throw error
      }
    }
  })

  // 测试获取不存在的团队
  it('获取不存在的团队应该返回404', async () => {
    try {
      await api.get<Team>('/teams/99999')
    } catch (error) {
      if (axios.isAxiosError(error)) {
        expect(error.response?.status).toBe(404)
      } else {
        throw error
      }
    }
  })
}) 