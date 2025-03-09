import axios from 'axios';
import { API_BASE_URL } from '../config';
import { WorkflowCreate, WorkflowUpdate, WorkflowNodeCreate, LedgerSubmit, LedgerApproval } from '../types';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// 请求拦截器，添加token到请求头
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token
      : null;
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器，处理错误
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 处理401错误，清除token并跳转到登录页
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 获取工作流列表
export async function getWorkflows() {
  const response = await api.get('/workflows/');
  return response.data;
}

// 获取工作流详情
export async function getWorkflow(id: number) {
  const response = await api.get(`/workflows/${id}`);
  return response.data;
}

// 创建工作流
export async function createWorkflow(workflow: WorkflowCreate) {
  const response = await api.post('/workflows/', workflow);
  return response.data;
}

// 更新工作流
export async function updateWorkflow(id: number, workflow: WorkflowUpdate) {
  const response = await api.put(`/workflows/${id}`, workflow);
  return response.data;
}

// 删除工作流
export async function deleteWorkflow(id: number) {
  const response = await api.delete(`/workflows/${id}`);
  return response.data;
}

// 获取工作流节点
export async function getWorkflowNodes(workflowId: number) {
  const response = await api.get(`/workflows/${workflowId}/nodes`);
  return response.data;
}

// 创建工作流节点
export async function createWorkflowNode(workflowId: number, node: WorkflowNodeCreate) {
  const response = await api.post(`/workflows/${workflowId}/nodes`, node);
  return response.data;
}

// 更新工作流节点
export async function updateWorkflowNode(workflowId: number, nodeId: number, node: Partial<WorkflowNodeCreate>) {
  const response = await api.put(`/workflows/${workflowId}/nodes/${nodeId}`, node);
  return response.data;
}

// 删除工作流节点
export async function deleteWorkflowNode(workflowId: number, nodeId: number) {
  const response = await api.delete(`/workflows/${workflowId}/nodes/${nodeId}`);
  return response.data;
}

// 获取工作流实例
export async function getWorkflowInstances(ledgerId: number) {
  const response = await api.get(`/ledgers/${ledgerId}/workflows`);
  return response.data;
}

// 获取工作流实例详情
export async function getWorkflowInstance(instanceId: number) {
  const response = await api.get(`/workflow-instances/${instanceId}`);
  return response.data;
}

// 提交台账审批
export async function submitLedgerForApproval(ledgerId: number, data: LedgerSubmit) {
  const response = await api.post(`/ledgers/${ledgerId}/submit`, data);
  return response.data;
}

// 处理台账审批
export async function processApproval(ledgerId: number, data: LedgerApproval) {
  const response = await api.post(`/ledgers/${ledgerId}/approve`, data);
  return response.data;
}

// 获取用户的待审批任务
export async function getPendingApprovals() {
  const response = await api.get('/workflow-instances/pending');
  return response.data;
}

// 获取工作流节点的审批人
export async function getNodeApprovers(nodeId: number) {
  try {
    console.log(`正在请求节点ID=${nodeId}的审批人列表...`);
    const response = await api.get(`/workflow-nodes/${nodeId}/approvers`);
    console.log('获取审批人列表成功:', response.data);
    return response.data;
  } catch (error) {
    console.error(`获取节点ID=${nodeId}的审批人列表失败:`, error);
    if (axios.isAxiosError(error)) {
      console.error('错误状态码:', error.response?.status);
      console.error('错误详情:', error.response?.data);
    }
    throw error;
  }
}

// 添加审批人到工作流节点
export async function addNodeApprovers(nodeId: number, userId: number) {
  try {
    console.log(`正在添加用户ID=${userId}到节点ID=${nodeId}的审批人...`);
    const response = await api.post(`/workflow-nodes/${nodeId}/approvers`, { user_id: userId });
    return response.data;
  } catch (error) {
    console.error(`添加审批人失败:`, error);
    if (axios.isAxiosError(error)) {
      console.error('错误状态码:', error.response?.status);
      console.error('错误详情:', error.response?.data);
    }
    throw error;
  }
}

// 更新工作流节点的审批人列表
export async function updateNodeApprovers(nodeId: number, userIds: number[]) {
  try {
    console.log(`正在更新节点ID=${nodeId}的审批人列表...`, userIds);
    const response = await api.put(`/workflow-nodes/${nodeId}/approvers`, { user_ids: userIds });
    return response.data;
  } catch (error) {
    console.error(`更新审批人列表失败:`, error);
    if (axios.isAxiosError(error)) {
      console.error('错误状态码:', error.response?.status);
      console.error('错误详情:', error.response?.data);
    }
    throw error;
  }
}

// 删除工作流节点的审批人
export async function removeNodeApprover(nodeId: number, userId: number) {
  try {
    console.log(`正在从节点ID=${nodeId}移除用户ID=${userId}...`);
    const response = await api.delete(`/workflow-nodes/${nodeId}/approvers?user_id=${userId}`);
    return response.data;
  } catch (error) {
    console.error(`移除审批人失败:`, error);
    if (axios.isAxiosError(error)) {
      console.error('错误状态码:', error.response?.status);
      console.error('错误详情:', error.response?.data);
    }
    throw error;
  }
}

// 获取模板列表
export async function getTemplates() {
  const response = await api.get('/templates/');
  return response.data;
}

// 获取角色列表
export async function getRoles() {
  const response = await api.get('/roles/');
  return response.data;
}

// 获取用户列表
export async function getUsers() {
  const response = await api.get('/users/');
  return response.data;
} 