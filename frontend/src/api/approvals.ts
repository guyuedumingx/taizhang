import axios from 'axios';
import { API_BASE_URL } from '../config';
import { Ledger, LedgerSubmit, LedgerApproval, AuditLog } from '../types';

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
export async function approveLedger(ledgerId: number, data: LedgerApproval) {
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