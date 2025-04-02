import * as approvalsAPI from '../api/approvals';
import * as workflowInstancesAPI from '../api/workflow_instances';
import { WorkflowInstance, LedgerApproval, WorkflowNodeApproval, WorkflowNodeRejection, Ledger, LedgerSubmit } from '../types';

export class ApprovalService {
  // 获取用户待办任务
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

  // 获取工作流实例详情
  static async getWorkflowInstance(instanceId: number): Promise<WorkflowInstance> {
    try {
      return await workflowInstancesAPI.getWorkflowInstance(instanceId);
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
  static async submitLedgerForApproval(ledgerId: number, data: LedgerSubmit) {
    try {
      return await approvalsAPI.submitLedgerForApproval(ledgerId, data);
    } catch (error) {
      console.error(`提交台账 ${ledgerId} 进入审批流程失败:`, error);
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
  static async approveWorkflowNode(instanceId: number, nodeId: number, approvalData: WorkflowNodeApproval) {
    try {
      return await workflowInstancesAPI.approveWorkflowNode(instanceId, nodeId, approvalData);
    } catch (error) {
      console.error(`审批通过工作流实例 ${instanceId} 节点 ${nodeId} 失败:`, error);
      throw error;
    }
  }

  // 拒绝工作流节点
  static async rejectWorkflowNode(instanceId: number, nodeId: number, rejectionData: WorkflowNodeRejection) {
    try {
      return await workflowInstancesAPI.rejectWorkflowNode(instanceId, nodeId, rejectionData);
    } catch (error) {
      console.error(`拒绝工作流实例 ${instanceId} 节点 ${nodeId} 失败:`, error);
      throw error;
    }
  }
}