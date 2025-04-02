import axios from 'axios';
import { API_BASE_URL } from '../config';
import { WorkflowInstance, WorkflowNodeApproval, WorkflowNodeRejection } from '../types';

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