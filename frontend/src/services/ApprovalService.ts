import * as approvalsAPI from '../api/approvals';
import * as workflowInstancesAPI from '../api/workflow_instances';
import axios from 'axios';
import { WorkflowInstance, LedgerApproval, WorkflowNodeApproval, WorkflowNodeRejection, Ledger, LedgerSubmit } from '../types';

interface ApprovalResult {
  success: boolean;
  message: string;
}

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
      const response = await approvalsAPI.getPendingTasks();
      return response.data;
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

  // 获取工作流实例详情
  static async getWorkflowInstance(instanceId: number) {
    try {
      const response = await axios.get(`/api/workflow/instances/${instanceId}`);
      return response.data;
    } catch (error) {
      console.error(`获取工作流实例 ${instanceId} 详情失败:`, error);
      throw error;
    }
  }

  // 获取台账的工作流实例
  static async getWorkflowInstanceByLedger(ledgerId: number): Promise<WorkflowInstance> {
    try {
      return await workflowInstancesAPI.getWorkflowInstanceByLedger(ledgerId);
    } catch (error) {
      console.error(`获取台账 ${ledgerId} 的工作流实例失败:`, error);
      throw error;
    }
  }

  // 获取工作流实例节点
  static async getWorkflowInstanceNodes(instanceId: number) {
    try {
      return await workflowInstancesAPI.getWorkflowInstanceNodes(instanceId);
    } catch (error) {
      console.error(`获取工作流实例 ${instanceId} 节点失败:`, error);
      throw error;
    }
  }

  // 提交台账进入审批流程
  static async submitLedgerForApproval(ledgerId: number, data: SubmitApprovalData) {
    try {
      const response = await fetch(`/api/ledgers/${ledgerId}/submit-approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await response.json();
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

  // 获取台账审计日志
  static async getLedgerAuditLogs(ledgerId: number) {
    try {
      return await approvalsAPI.getLedgerAuditLogs(ledgerId);
    } catch (error) {
      console.error(`获取台账 ${ledgerId} 审计日志失败:`, error);
      throw error;
    }
  }

  // 审批通过工作流节点
  static async approveWorkflowNode(instanceId: number, taskId: number, data: ApprovalData) {
    try {
      const response = await fetch(`/api/workflow/instances/${instanceId}/tasks/${taskId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      console.error(`审批通过工作流实例 ${instanceId} 节点 ${taskId} 失败:`, error);
      throw error;
    }
  }

  // 拒绝工作流节点
  static async rejectWorkflowNode(instanceId: number, taskId: number, data: ApprovalData) {
    try {
      const response = await fetch(`/api/workflow/instances/${instanceId}/tasks/${taskId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      console.error(`拒绝工作流实例 ${instanceId} 节点 ${taskId} 失败:`, error);
      throw error;
    }
  }

  // 统一处理台账审批（可用于通过或拒绝）
  static async processLedgerApproval(ledgerId: number, instanceId: number, data: ApprovalData) {
    const action = data.action || 'approve';
    try {
      const response = await fetch(`/api/ledgers/${ledgerId}/workflow/instances/${instanceId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      console.error(`处理台账 ${ledgerId} 审批失败:`, error);
      throw error;
    }
  }

  // 获取工作流详情
  static async getWorkflow(workflowId: number) {
    try {
      const response = await fetch(`/api/workflows/${workflowId}`);
      return await response.json();
    } catch (error) {
      console.error(`获取工作流 ${workflowId} 详情失败:`, error);
      throw error;
    }
  }
}