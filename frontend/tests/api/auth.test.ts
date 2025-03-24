import { describe, it, expect } from 'vitest'
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

describe('认证 API 测试', () => {
  // 测试登录功能
  it('应该能成功登录系统', async () => {
    const formData = new URLSearchParams()
    formData.append('username', '1234567')  // EHR ID作为username
    formData.append('password', 'password123')
    
    const response = await api.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })

    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('access_token')
    expect(response.data).toHaveProperty('user_id')
    expect(response.data).toHaveProperty('username')
    expect(response.data).toHaveProperty('permissions')
  })

  // 测试登录失败的情况
  it('使用错误的凭据应该登录失败', async () => {
    try {
      const formData = createFormData('wrong_user', 'wrong_password')
      await api.post<LoginResponse>('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
    } catch (error) {
      if (axios.isAxiosError(error)) {
        expect(error.response?.status).toBe(400)
      } else {
        throw error
      }
    }
  })

  // 测试注册功能
  it('应该能成功注册新用户', async () => {
    const timestamp = Date.now().toString().slice(-7)  // 取后7位作为EHR ID
    const testUser = {
      username: `test_user_${timestamp}`,
      ehr_id: timestamp,  // 7位数字
      password: 'password123',
      name: '测试用户',
      department: '测试部门',
      roles: ['user']
    }

    const response = await api.post<User>('/auth/register', testUser)

    expect(response.status).toBe(200)
    expect(response.data).toHaveProperty('id')
    expect(response.data.username).toBe(testUser.username)
    expect(response.data.ehr_id).toBe(testUser.ehr_id)
  })

  // 测试重复注册
  it('注册重复用户名应该失败', async () => {
    const testUser = {
      username: 'testuser',
      ehr_id: '1234567',  // 7位数字
      password: 'password123',
      name: '测试用户',
      department: '测试部门',
      roles: ['user']
    }

    const response = await api.post<User>('/auth/register', testUser)
    expect(response.status).toBe(400)
  })
}) 