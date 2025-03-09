import axios from 'axios';
import { API_BASE_URL } from '../config';

// 获取台账审计日志
export async function getLedgerAuditLogs(id: number) {
  const token = localStorage.getItem('auth-storage')
    ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token
    : null;
    
  const response = await axios.get(`${API_BASE_URL}/logs/audit/ledger/${id}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data;
} 