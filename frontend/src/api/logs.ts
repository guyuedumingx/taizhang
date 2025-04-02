import axios from 'axios';
import { API_BASE_URL } from '../config';
import { SystemLog, AuditLog, LogQueryParams } from '../types';

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

// 构建查询参数
const buildQueryParams = (params?: Record<string, any>): string => {
  if (!params) return '';
  
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
    .join('&');
  
  return query ? `?${query}` : '';
};

// 获取系统日志
export async function getSystemLogs(params?: LogQueryParams) {
  const query = buildQueryParams(params);
  const response = await api.get(`/logs/system${query}`);
  return response.data;
}

// 统计系统日志数量
export async function countSystemLogs(params?: LogQueryParams) {
  const query = buildQueryParams(params);
  const response = await api.get(`/logs/system/count${query}`);
  return response.data;
}

// 获取最近系统日志
export async function getRecentSystemLogs(days = 7, limit = 100) {
  const response = await api.get(`/logs/system/recent?days=${days}&limit=${limit}`);
  return response.data;
}

// 获取错误日志
export async function getErrorLogs(days = 7, limit = 100) {
  const response = await api.get(`/logs/system/errors?days=${days}&limit=${limit}`);
  return response.data;
}

// 获取资源日志
export async function getResourceLogs(resourceType: string, resourceId: string, limit = 100) {
  const response = await api.get(`/logs/system/resource/${resourceType}/${resourceId}?limit=${limit}`);
  return response.data;
}

// 获取审计日志
export async function getAuditLogs(params?: Record<string, any>) {
  const query = buildQueryParams(params);
  const response = await api.get(`/logs/audit${query}`);
  return response.data;
} 