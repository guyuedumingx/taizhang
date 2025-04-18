import { LedgerApproval } from '../types';
import { api } from './index';
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

// 获取用户的待办任务
export async function getPendingTasks() {
  try {
    const response = await api.get('/approvals/tasks');
    return response.data;
  } catch (error) {
    console.error('获取待办任务失败:', error);
    throw error;
  }
}

// 获取用户需要审批的台账列表
export async function getApprovalLedgers(skip = 0, limit = 100, status?: string) {
  try {
    let url = `/approvals/ledgers?skip=${skip}&limit=${limit}`;
    if (status) {
      url += `&status=${status}`;
    }
    const response = await api.get(url);
    return response.data;
  } catch (error) {
    console.error('获取待审批台账失败:', error);
    throw error;
  }
}

// 提交台账进入审批流程
export async function submitLedgerForApproval(ledgerId: number, data: SubmitApprovalData) {
  try {
    const response = await api.post(`/approvals/ledgers/${ledgerId}/submit`, data);
    return response.data;
  } catch (error) {
    console.error(`提交台账 ${ledgerId} 审批失败:`, error);
    throw error;
  }
}

// 审批台账
export async function approveLedger(ledgerId: number, data: LedgerApproval) {
  try {
    const response = await api.post(`/approvals/ledgers/${ledgerId}/approve`, data);
    return response.data;
  } catch (error) {
    console.error(`审批通过台账 ${ledgerId} 失败:`, error);
    throw error;
  }
}

// 取消台账审批流程
export async function cancelApproval(ledgerId: number) {
  try {
    const response = await api.post(`/approvals/ledgers/${ledgerId}/cancel`, {});
    return response.data;
  } catch (error) {
    console.error(`取消台账 ${ledgerId} 审批失败:`, error);
    throw error;
  }
}