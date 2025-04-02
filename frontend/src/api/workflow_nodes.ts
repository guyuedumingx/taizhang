import axios from 'axios';
import { API_BASE_URL } from '../config';
import { WorkflowNode } from '../types';

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