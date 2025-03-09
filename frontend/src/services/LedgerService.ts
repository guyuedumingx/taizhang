import api from '../api';
import { Ledger, LedgerCreate, LedgerUpdate } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class LedgerService {
  // 获取台账列表
  static async getLedgers(params?: QueryParams): Promise<Ledger[]> {
    try {
      return await api.ledgers.getLedgers(params);
    } catch (error) {
      console.error('获取台账列表失败:', error);
      throw error;
    }
  }

  // 获取台账详情
  static async getLedger(id: number): Promise<Ledger> {
    try {
      return await api.ledgers.getLedger(id);
    } catch (error) {
      console.error(`获取台账 ${id} 详情失败:`, error);
      throw error;
    }
  }

  // 创建台账
  static async createLedger(data: LedgerCreate): Promise<Ledger> {
    try {
      return await api.ledgers.createLedger(data);
    } catch (error) {
      console.error('创建台账失败:', error);
      throw error;
    }
  }

  // 更新台账
  static async updateLedger(id: number, data: LedgerUpdate): Promise<Ledger> {
    try {
      return await api.ledgers.updateLedger(id, data);
    } catch (error) {
      console.error(`更新台账 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除台账
  static async deleteLedger(id: number): Promise<void> {
    try {
      await api.ledgers.deleteLedger(id);
    } catch (error) {
      console.error(`删除台账 ${id} 失败:`, error);
      throw error;
    }
  }

  // 导出台账
  static async exportLedger(id: number, format: string): Promise<Blob> {
    try {
      return await api.ledgers.exportLedger(id, format);
    } catch (error) {
      console.error(`导出台账 ${id} 失败:`, error);
      throw error;
    }
  }

  // 导出所有台账
  static async exportAllLedgers(format: string, templateId?: number): Promise<Blob> {
    try {
      return await api.ledgers.exportAllLedgers(format, templateId);
    } catch (error) {
      console.error('导出所有台账失败:', error);
      throw error;
    }
  }

  // 根据模板获取台账列表
  static async getLedgersByTemplate(templateId: number): Promise<Ledger[]> {
    try {
      return await api.ledgers.getLedgers({ template_id: templateId });
    } catch (error) {
      console.error(`获取模板 ${templateId} 的台账列表失败:`, error);
      throw error;
    }
  }
} 