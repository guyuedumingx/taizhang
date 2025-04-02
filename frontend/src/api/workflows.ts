import axios from 'axios';
import { API_BASE_URL } from '../config';
import { 
  WorkflowCreate, 
  WorkflowUpdate, 
  LedgerSubmit, 
  LedgerApproval, 
  WorkflowNodeApproval, 
  WorkflowNodeRejection 
} from '../types';

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

// ----------------- 工作流管理API -----------------

// 获取工作流列表
export async function getWorkflows(skip = 0, limit = 100) {
  const response = await api.get(`/workflows/?skip=${skip}&limit=${limit}`);
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
  await api.delete(`/workflows/${id}`);
  return null;
}

// ----------------- 工作流节点API -----------------

// 获取工作流节点详情
export async function getWorkflowNode(nodeId: number) {
  const response = await api.get(`/workflow-nodes/${nodeId}`);
  return response.data;
}

// 获取工作流节点的审批人列表
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

// ----------------- 工作流实例API -----------------

// 获取工作流实例详情
export async function getWorkflowInstance(instanceId: number) {
  const response = await api.get(`/workflow-instances/${instanceId}`);
  return response.data;
}

// 获取台账的工作流实例
export async function getWorkflowInstanceByLedger(ledgerId: number) {
  const response = await api.get(`/workflow-instances/ledger/${ledgerId}`);
  return response.data;
}

// 获取工作流实例的节点列表
export async function getWorkflowInstanceNodes(instanceId: number) {
  const response = await api.get(`/workflow-instances/${instanceId}/nodes`);
  return response.data;
}

// 审批通过工作流节点
export async function approveWorkflowNode(instanceId: number, nodeId: number, approvalData: WorkflowNodeApproval) {
  const response = await api.post(`/workflow-instances/${instanceId}/nodes/${nodeId}/approve`, approvalData);
  return response.data;
}

// 拒绝工作流节点
export async function rejectWorkflowNode(instanceId: number, nodeId: number, rejectionData: WorkflowNodeRejection) {
  const response = await api.post(`/workflow-instances/${instanceId}/nodes/${nodeId}/reject`, rejectionData);
  return response.data;
}

// ----------------- 审批相关API -----------------

// 获取用户的待办任务
export async function getPendingTasks() {
  const response = await api.get('/approvals/tasks');
  return response.data;
}

// 获取用户需要审批的台账列表
export async function getApprovalLedgers(skip = 0, limit = 100, status?: string) {
  let url = `/approvals/ledgers?skip=${skip}&limit=${limit}`;
  if (status) {
    url += `&status=${status}`;
  }
  const response = await api.get(url);
  return response.data;
}

// 提交台账进入审批流程
export async function submitLedgerForApproval(ledgerId: number, data: LedgerSubmit) {
  const response = await api.post(`/approvals/ledgers/${ledgerId}/submit`, data);
  return response.data;
}

// 审批台账
export async function processApproval(ledgerId: number, data: LedgerApproval) {
  const response = await api.post(`/approvals/ledgers/${ledgerId}/approve`, data);
  return response.data;
}

// 取消台账审批流程
export async function cancelApproval(ledgerId: number) {
  const response = await api.post(`/approvals/ledgers/${ledgerId}/cancel`, {});
  return response.data;
}

// 获取台账的审计日志
export async function getLedgerAuditLogs(ledgerId: number) {
  const response = await api.get(`/approvals/audit-logs/${ledgerId}`);
  return response.data;
}

// ----------------- 辅助工具API -----------------

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