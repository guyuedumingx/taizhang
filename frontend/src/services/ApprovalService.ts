import axios from 'axios';
import { API_BASE_URL } from '../config';

export class ApprovalService {
  // 获取待办任务
  static async getPendingTasks() {
    try {
      const response = await axios.get(`${API_BASE_URL}/approvals/tasks`, {
        headers: this.getAuthHeader()
      });
      return response.data;
    } catch (error) {
      console.error('获取待办任务失败:', error);
      throw error;
    }
  }

  // 获取待审批台账
  static async getPendingLedgers() {
    try {
      const response = await axios.get(`${API_BASE_URL}/approvals/ledgers`, {
        headers: this.getAuthHeader()
      });
      return response.data;
    } catch (error) {
      console.error('获取待审批台账失败:', error);
      throw error;
    }
  }

  // 提交台账审批
  static async submitLedgerForApproval(ledgerId: number, workflowId: number) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/approvals/ledgers/${ledgerId}/submit`,
        { workflow_id: workflowId },
        { headers: this.getAuthHeader() }
      );
      return response.data;
    } catch (error) {
      console.error('提交台账审批失败:', error);
      throw error;
    }
  }

  // 审批通过工作流节点
  static async approveWorkflowNode(instanceId: number, nodeId: number, data: { comment: string, next_approver_id?: number }) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/approvals/workflow-instances/${instanceId}/nodes/${nodeId}/approve`,
        data,
        { headers: this.getAuthHeader() }
      );
      return response.data;
    } catch (error) {
      console.error('审批通过工作流节点失败:', error);
      throw error;
    }
  }

  // 拒绝工作流节点
  static async rejectWorkflowNode(instanceId: number, nodeId: number, data: { comment: string }) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/approvals/workflow-instances/${instanceId}/nodes/${nodeId}/reject`,
        data,
        { headers: this.getAuthHeader() }
      );
      return response.data;
    } catch (error) {
      console.error('拒绝工作流节点失败:', error);
      throw error;
    }
  }

  // 获取工作流实例
  static async getWorkflowInstance(instanceId: number) {
    try {
      const response = await axios.get(`${API_BASE_URL}/workflow-instances/${instanceId}`, {
        headers: this.getAuthHeader()
      });
      return response.data;
    } catch (error) {
      console.error('获取工作流实例失败:', error);
      throw error;
    }
  }

  // 获取台账的工作流实例
  static async getLedgerWorkflowInstance(ledgerId: number) {
    try {
      const response = await axios.get(`${API_BASE_URL}/workflow-instances/ledger/${ledgerId}`, {
        headers: this.getAuthHeader()
      });
      return response.data;
    } catch (error) {
      console.error('获取台账工作流实例失败:', error);
      throw error;
    }
  }

  // 获取认证头
  private static getAuthHeader() {
    const token = localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token
      : null;
    
    return {
      Authorization: `Bearer ${token}`
    };
  }
} 