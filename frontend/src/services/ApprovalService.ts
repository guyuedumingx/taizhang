import api from '../api';
import { Ledger, LedgerSubmit, LedgerApproval, AuditLog, WorkflowInstance } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class ApprovalService {
  // 获取待办任务
  static async getPendingTasks(): Promise<Record<string, unknown>[]> {
    try {
      return await api.approvals.getPendingTasks();
    } catch (error) {
      console.error('获取待办任务失败:', error);
      throw error;
    }
  }

  // 获取待审批台账
  static async getApprovalLedgers(params?: QueryParams): Promise<Ledger[]> {
    try {
      return await api.approvals.getApprovalLedgers(params);
    } catch (error) {
      console.error('获取待审批台账失败:', error);
      throw error;
    }
  }

  // 提交台账审批
  static async submitLedger(ledgerId: number, data: LedgerSubmit): Promise<Ledger> {
    try {
      return await api.approvals.submitLedger(ledgerId, data);
    } catch (error) {
      console.error(`提交台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }

  // 审批台账
  static async approveLedger(ledgerId: number, data: LedgerApproval): Promise<Ledger> {
    try {
      return await api.approvals.approveLedger(ledgerId, data);
    } catch (error) {
      console.error(`审批台账 ${ledgerId} 失败:`, error);
      throw error;
    }
  }

  // 取消审批
  static async cancelApproval(ledgerId: number): Promise<Ledger> {
    try {
      return await api.approvals.cancelApproval(ledgerId);
    } catch (error) {
      console.error(`取消台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }

  // 获取工作流实例
  static async getWorkflowInstance(instanceId: number): Promise<WorkflowInstance> {
    try {
      return await api.approvals.getWorkflowInstance(instanceId);
    } catch (error) {
      console.error(`获取工作流实例 ${instanceId} 失败:`, error);
      throw error;
    }
  }

  // 获取台账审计日志
  static async getLedgerAuditLogs(ledgerId: number): Promise<AuditLog[]> {
    try {
      return await api.approvals.getLedgerAuditLogs(ledgerId);
    } catch (error) {
      console.error(`获取台账 ${ledgerId} 审计日志失败:`, error);
      throw error;
    }
  }
} 