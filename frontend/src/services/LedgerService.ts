import * as ledgersAPI from '../api/ledgers';
import { Ledger, LedgerCreate, LedgerUpdate, AuditLog } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class LedgerService {
  // 获取台账列表
  static async getLedgers(params?: QueryParams): Promise<Ledger[]> {
      const response = await ledgersAPI.getLedgers(params || {});
      console.log('Ledgers API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取ledgers数组');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error('API返回的ledgers格式不正确:', response);
      return [];
  }

  // 获取台账详情
  static async getLedger(id: number): Promise<Ledger> {
    return await ledgersAPI.getLedger(id);
  }

  // 获取台账审计日志
  static async getLedgerAuditLogs(id: number): Promise<AuditLog[]> {
    return await ledgersAPI.getLedgerAuditLogs(id);
  }

  // 创建台账
  static async createLedger(data: LedgerCreate): Promise<Ledger> {
    return await ledgersAPI.createLedger(data);
  }

  // 更新台账
  static async updateLedger(id: number, data: LedgerUpdate): Promise<Ledger> {
    return await ledgersAPI.updateLedger(id, data);
  }

  // 删除台账
  static async deleteLedger(id: number): Promise<void> {
    await ledgersAPI.deleteLedger(id);
  }

  // 导出台账
  static async exportLedger(id: number, format: string): Promise<Blob> {
    return await ledgersAPI.exportLedger(id, format);
  }

  // 导出所有台账
  static async exportAllLedgers(format: string, templateId?: number): Promise<Blob> {
    return await ledgersAPI.exportAllLedgers(format, templateId);
  }

  // 根据模板获取台账列表
  static async getLedgersByTemplate(templateId: number): Promise<Ledger[]> {
    const response = await ledgersAPI.getLedgers({ template_id: templateId });
    console.log(`获取模板 ${templateId} 的台账列表返回数据:`, response);
    
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取ledgers数组');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error(`获取模板 ${templateId} 的台账列表返回格式不正确:`, response);
      return [];
  }
} 