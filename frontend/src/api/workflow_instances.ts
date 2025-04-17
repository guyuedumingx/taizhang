import { api } from './index';
import { WorkflowNodeApproval, WorkflowNodeRejection } from '../types';

// 获取工作流实例详情
export async function getWorkflowInstance(instanceId: number) {
  const response = await api.get(`/workflow-instances/${instanceId}`);
  return response.data;
}

// 获取台账的工作流实例
export async function getWorkflowInstanceByLedger(ledgerId: number) {
  const response = await api.get(`/workflow-instances/ledger/${ledgerId}`);
  return response.data;
}

// 获取工作流实例的节点列表
export async function getWorkflowInstanceNodes(instanceId: number) {
  const response = await api.get(`/workflow-instances/${instanceId}/nodes`);
  return response.data;
}

// 审批通过工作流节点
export async function approveWorkflowNode(instanceId: number, nodeId: number, approvalData: WorkflowNodeApproval) {
  const response = await api.post(`/workflow-instances/${instanceId}/nodes/${nodeId}/approve`, approvalData);
  return response.data;
}

// 拒绝工作流节点
export async function rejectWorkflowNode(instanceId: number, nodeId: number, rejectionData: WorkflowNodeRejection) {
  const response = await api.post(`/workflow-instances/${instanceId}/nodes/${nodeId}/reject`, rejectionData);
  return response.data;
} 