import { SystemLog, AuditLog, LogQueryParams } from '../types';
import * as LogsAPI from '../api/logs';

export class LogService {
  // 获取系统日志
  static async getSystemLogs(params?: LogQueryParams): Promise<{ 
    items: SystemLog[]; 
    total: number;
  }> {
    try {
      const response = await LogsAPI.getSystemLogs(params);
      // 处理不同的响应格式
      if (Array.isArray(response)) {
        console.log(response);
        return {
          items: response,
          total: response.length
        };
      }
      return response;
    } catch (error) {
      console.error('获取系统日志失败:', error);
      throw error;
    }
  }

  // 获取最近系统日志
  static async getRecentSystemLogs(count: number = 10): Promise<SystemLog[]> {
    try {
      return await LogsAPI.getRecentSystemLogs(count);
    } catch (error) {
      console.error('获取最近系统日志失败:', error);
      throw error;
    }
  }

  // 获取系统错误日志
  static async getSystemErrors(count: number = 10): Promise<SystemLog[]> {
    try {
      // 使用正确的API方法
      return await LogsAPI.getErrorLogs(undefined, count);
    } catch (error) {
      console.error('获取系统错误日志失败:', error);
      throw error;
    }
  }

  // 获取审计日志
  static async getAuditLogs(params?: LogQueryParams): Promise<{ 
    items: AuditLog[]; 
    total: number;
  }> {
    try {
      const response = await LogsAPI.getAuditLogs(params);
      // 处理不同的响应格式
      if (Array.isArray(response)) {
        return {
          items: response,
          total: response.length
        };
      }
      return response;
    } catch (error) {
      console.error('获取审计日志失败:', error);
      throw error;
    }
  }

  // 获取台账审计日志
  static async getLedgerAuditLogs(ledgerId: number): Promise<AuditLog[]> {
    try {
      // 使用正确的API方法
      return await LogsAPI.getResourceLogs('ledger', ledgerId.toString());
    } catch (error) {
      console.error(`获取台账 ${ledgerId} 审计日志失败:`, error);
      throw error;
    }
  }

  // 格式化日志级别
  static formatLogLevel(level: string): {
    color: string;
    label: string;
  } {
    switch (level.toLowerCase()) {
      case 'debug':
        return { color: 'blue', label: '调试' };
      case 'info':
        return { color: 'green', label: '信息' };
      case 'warning':
        return { color: 'orange', label: '警告' };
      case 'error':
        return { color: 'red', label: '错误' };
      case 'critical':
        return { color: 'purple', label: '严重' };
      default:
        return { color: 'default', label: level };
    }
  }

  // 格式化操作类型
  static formatActionType(action: string): {
    color: string;
    label: string;
  } {
    switch (action) {
      case 'create':
        return { color: 'green', label: '创建' };
      case 'update':
        return { color: 'blue', label: '更新' };
      case 'delete':
        return { color: 'red', label: '删除' };
      case 'view':
        return { color: 'grey', label: '查看' };
      case 'login':
        return { color: 'cyan', label: '登录' };
      case 'logout':
        return { color: 'purple', label: '登出' };
      case 'submit':
        return { color: 'orange', label: '提交' };
      case 'approve':
        return { color: 'green', label: '批准' };
      case 'reject':
        return { color: 'red', label: '拒绝' };
      default:
        return { color: 'default', label: action };
    }
  }

  // 格式化日期时间
  static formatDateTime(dateTime: string): string {
    if (!dateTime) return '';
    
    const date = new Date(dateTime);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }
} 