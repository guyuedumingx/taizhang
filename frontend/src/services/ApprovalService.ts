import * as approvalsAPI from '../api/approvals';
import {  LedgerApproval } from '../types';

// 定义approval数据接口
export interface ApprovalData {
  action?: 'approve' | 'reject';
  comment?: string;
  next_approver_id?: number;
}

// 定义提交审批数据接口
export interface SubmitApprovalData {
  workflow_id: number;
  comment?: string;
  next_approver_id?: number;
}

export class ApprovalService {
  // 获取当前用户的待办任务
  static async getPendingTasks() {
    try {
      return await approvalsAPI.getPendingTasks();
    } catch (error) {
      console.error('获取待办任务失败:', error);
      throw error;
    }
  }

  // 获取用户待审批台账
  static async getApprovalLedgers(skip = 0, limit = 100, status?: string) {
    try {
      return await approvalsAPI.getApprovalLedgers(skip, limit, status);
    } catch (error) {
      console.error('获取待审批台账失败:', error);
      throw error;
    }
  }

  // 提交台账进入审批流程
  static async submitLedgerForApproval(ledgerId: number, data: SubmitApprovalData) {
    try {
      return approvalsAPI.submitLedgerForApproval(ledgerId, data)
    } catch (error) {
      console.error(`提交台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }

  // 审批通过台账
  static async approveLedger(ledgerId: number, data: LedgerApproval) {
    try {
      return await approvalsAPI.approveLedger(ledgerId, data);
    } catch (error) {
      console.error(`审批通过台账 ${ledgerId} 失败:`, error);
      throw error;
    }
  }

  // 取消台账审批
  static async cancelApproval(ledgerId: number) {
    try {
      return await approvalsAPI.cancelApproval(ledgerId);
    } catch (error) {
      console.error(`取消台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }

  // 审批通过工作流节点
  static async approveWorkflowNode(instanceId: number, taskId: number, data: ApprovalData) {
    try {
      return await approvalsAPI.approveWorkflowNode(instanceId, taskId, data)
    } catch (error) {
      console.error(`审批通过工作流实例 ${instanceId} 节点 ${taskId} 失败:`, error);
      throw error;
    }
  }

  // 拒绝工作流节点
  static async rejectWorkflowNode(instanceId: number, taskId: number, data: ApprovalData) {
    try {
      return await approvalsAPI.rejectWorkflowNode(instanceId, taskId, data)
    } catch (error) {
      console.error(`拒绝工作流实例 ${instanceId} 节点 ${taskId} 失败:`, error);
      throw error;
    }
  }

  // 统一处理台账审批（可用于通过或拒绝）
  static async processLedgerApproval(ledgerId: number, instanceId: number, data: ApprovalData) {
    try {
      return await approvalsAPI.processLedgerApproval(ledgerId, instanceId, data)
    } catch (error) {
      console.error(`处理台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }
}