import { describe, it, expect, beforeAll } from 'vitest'
import api from '../../src/api'
import type { AxiosError } from 'axios'

describe('工作流管理 API 测试', () => {
  let testWorkflowId: number
  let testNodeId: number
  let testUserId: number
  let testTemplateId: number

  // 在所有测试开始前登录获取 token
  beforeAll(async () => {
    // 登录获取 token
    await api.auth.login('1234567', 'password123')

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
    const userResponse = await api.users.createUser(newUser)
    testUserId = userResponse.id

    // 创建测试模板
    const newTemplate = {
      name: `测试模板${Date.now()}`,
      description: '这是一个测试模板',
      department: '测试部门',
      fields: [
        {
          name: 'field1',
          type: 'text',
          label: '字段1',
          required: true,
          order: 0,
          is_key_field: true
        }
      ]
    }
    const templateResponse = await api.templates.createTemplate(newTemplate)
    testTemplateId = templateResponse.id
  })

  // 测试获取工作流列表
  it('应该能获取工作流列表', async () => {
    const response = await api.workflows.getWorkflows()
    
    expect(Array.isArray(response)).toBe(true)
  })

  // 测试创建工作流
  it('应该能创建新工作流', async () => {
    const newWorkflow = {
      name: `测试工作流${Date.now()}`,
      description: '这是一个测试工作流',
      template_id: testTemplateId,
      is_active: true,
      nodes: []  // 添加空的节点列表
    }

    const response = await api.workflows.createWorkflow(newWorkflow)
    
    expect(response).toHaveProperty('id')
    expect(response.name).toBe(newWorkflow.name)
    
    testWorkflowId = response.id
  })

  // 测试获取单个工作流
  it('应该能获取指定工作流', async () => {
    const response = await api.workflows.getWorkflow(testWorkflowId)
    
    expect(response).toHaveProperty('id', testWorkflowId)
  })

  // 测试更新工作流
  it('应该能更新工作流信息', async () => {
    const updateData = {
      name: '更新后的工作流名称',
      description: '更新后的工作流描述',
      is_active: true
    }

    const response = await api.workflows.updateWorkflow(testWorkflowId, updateData)
    
    expect(response.name).toBe(updateData.name)
    expect(response.description).toBe(updateData.description)
  })

  // 测试创建工作流节点
  it('应该能创建工作流节点', async () => {
    const newNode = {
      name: '审批节点1',
      node_type: 'approval',
      order_index: 1,
      description: '这是第一个审批节点',
      workflow_id: testWorkflowId,
      is_final: false,
      multi_approve_type: 'any',
      need_select_next_approver: false
    }

    const response = await api.workflows.createWorkflowNode(testWorkflowId, newNode)
    
    expect(response).toHaveProperty('id')
    expect(response.name).toBe(newNode.name)
    
    testNodeId = response.id
  })

  // 测试获取工作流节点
  it('应该能获取工作流节点列表', async () => {
    const response = await api.workflows.getWorkflowNodes(testWorkflowId)
    
    expect(Array.isArray(response)).toBe(true)
    expect(response.length).toBeGreaterThan(0)
  })

  // 测试删除工作流节点
  it('应该能删除工作流节点', async () => {
    await api.workflows.deleteWorkflowNode(testWorkflowId, testNodeId)

    // 验证节点已被删除
    try {
      await api.workflows.getWorkflowNodes(testWorkflowId)
    } catch (error) {
      const axiosError = error as AxiosError
      expect(axiosError.response?.status).toBe(404)
    }
  })

  // 测试删除工作流
  it('应该能删除工作流', async () => {
    await api.workflows.deleteWorkflow(testWorkflowId)

    // 验证工作流已被删除
    try {
      await api.workflows.getWorkflow(testWorkflowId)
    } catch (error) {
      const axiosError = error as AxiosError
      expect(axiosError.response?.status).toBe(404)
    }
  })

  // 测试获取不存在的工作流
  it('获取不存在的工作流应该返回404', async () => {
    try {
      await api.workflows.getWorkflow(99999)
    } catch (error) {
      const axiosError = error as AxiosError
      expect(axiosError.response?.status).toBe(404)
    }
  })
}) 