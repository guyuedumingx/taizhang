import axios from 'axios';
import { API_BASE_URL } from '../config';
import { Ledger, LedgerCreate, LedgerUpdate, AuditLog } from '../types';
import { QueryParams, buildQueryParams } from './util';

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

// 获取台账列表
export async function getLedgers(queryParams: QueryParams) {
  const query = buildQueryParams(queryParams);
  const response = await api.get(`/ledgers/${query}`);
  return response.data;
}

// 获取台账详情
export async function getLedger(id: number) {
  const response = await api.get(`/ledgers/${id}`);
  return response.data;
}

// 创建台账
export async function createLedger(data: LedgerCreate) {
  const response = await api.post('/ledgers/', data);
  return response.data;
}

// 更新台账
export async function updateLedger(id: number, data: LedgerUpdate) {
  const response = await api.put(`/ledgers/${id}`, data);
  return response.data;
}

// 删除台账
export async function deleteLedger(id: number) {
  await api.delete(`/ledgers/${id}`);
  return null;
}

// 获取台账审计日志
export async function getLedgerAuditLogs(id: number) {
  const response = await api.get(`/logs/audit/ledger/${id}`);
  return response.data;
}

// 导出台账
export async function exportLedger(id: number, format: string) {
  const response = await api.get(`/ledgers/${id}/export?format=${format}`, {
    responseType: 'blob',
    headers: {
      'Accept': format.toLowerCase() === 'excel' ? 
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 
        format.toLowerCase() === 'csv' ? 
          'text/csv' : 'text/plain'
    }
  });
  return response.data;
}

// 导出所有台账
export async function exportAllLedgers(format: string, templateId?: number) {
  // 确保format参数是正确的值
  const safeFormat = format.toLowerCase();
  if (!['excel', 'csv', 'txt'].includes(safeFormat)) {
    throw new Error(`不支持的导出格式: ${format}，支持的格式：excel、csv、txt`);
  }
  
  try {
    // 构建基本URL
    let url = `/ledgers/export-all?format=${encodeURIComponent(safeFormat)}`;
    
    // 只在有效的情况下添加模板ID
    if (templateId !== undefined && templateId !== null) {
      // 确保是数字
      const numericTemplateId = Number(templateId);
      if (!isNaN(numericTemplateId)) {
        url += `&template_id=${numericTemplateId}`;
      }
    }
    
    const response = await api.get(url, {
      responseType: 'blob',
      headers: {
        'Accept': safeFormat === 'excel' ? 
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 
          safeFormat === 'csv' ? 'text/csv' : 'text/plain'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('API调用失败:', error);
    throw error;
  }
} 