import { describe, it, expect, beforeAll } from 'vitest'
import axios from 'axios'
import { API_BASE_URL } from '../../src/config'
import { LoginResponse, User } from '../../src/types'

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

describe('用户管理 API 测试', () => {
  let authToken: string
  let testUserId: number

  // 在所有测试开始前登录获取 token
  beforeAll(async () => {
    const formData = new URLSearchParams()
    formData.append('username', '1234567')  // EHR ID作为username
    formData.append('password', 'password123')
    
    const response = await api.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
    authToken = response.data.access_token
    api.defaults.headers.common['Authorization'] = `Bearer ${authToken}`
  })

  // 测试获取用户列表
  it('应该能获取用户列表', async () => {
    const response = await api.get<PaginatedResponse<User>>('/users/')
    
    expect(response.status).toBe(200)
    expect(Array.isArray(response.data.items)).toBe(true)
    expect(response.data.items.length).toBeGreaterThan(0)
    expect(response.data.items[0]).toHaveProperty('id')
    expect(response.data.items[0]).toHaveProperty('username')
  })

  // 测试创建用户
  it('应该能创建新用户', async () => {
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

    const response = await api.post<User>('/users/', newUser)
    
    expect(response.status).toBe(201)
    expect(response.data).toHaveProperty('id')
    expect(response.data.username).toBe(newUser.username)
    expect(response.data.name).toBe(newUser.name)
    
    testUserId = response.data.id
  })

  // 测试获取单个用户
  it('应该能获取指定用户', async () => {
    const response = await api.get<User>(`/users/${testUserId}`)
    
    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('id', testUserId)
  })

  // 测试更新用户
  it('应该能更新用户信息', async () => {
    const updateData = {
      name: '更新后的测试用户',
      department: '更新后的部门'
    }

    const response = await api.put<User>(`/users/${testUserId}`, updateData)
    
    expect(response.status).toBe(200)
    expect(response.data.name).toBe(updateData.name)
    expect(response.data.department).toBe(updateData.department)
  })

  // 测试删除用户
  it('应该能删除用户', async () => {
    const response = await api.delete(`/users/${testUserId}`)
    expect(response.status).toBe(204)

    // 验证用户已被删除
    try {
      await api.get<User>(`/users/${testUserId}`)
    } catch (error) {
      if (axios.isAxiosError(error)) {
        expect(error.response?.status).toBe(404)
      } else {
        throw error
      }
    }
  })

  // 测试获取不存在的用户
  it('获取不存在的用户应该返回404', async () => {
    try {
      await api.get<User>('/users/99999')
    } catch (error) {
      if (axios.isAxiosError(error)) {
        expect(error.response?.status).toBe(404)
      } else {
        throw error
      }
    }
  })
}) 