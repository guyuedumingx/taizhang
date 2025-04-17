import { api } from './index';

// 获取工作流节点详情
export async function getWorkflowNode(nodeId: number) {
  const response = await api.get(`/workflow-nodes/${nodeId}`);
  return response.data;
}

// 获取工作流节点的审批人列表
export async function getNodeApprovers(nodeId: number) {
  try {
    console.log(`正在请求节点ID=${nodeId}的审批人列表...`);
    const response = await api.get(`/workflow-nodes/${nodeId}/approvers`);
    console.log('获取审批人列表成功:', response.data);
    return response.data;
  } catch (error) {
    console.error(`获取节点ID=${nodeId}的审批人列表失败:`, error);
    throw error;
  }
}

// 更新工作流节点的审批人列表
export async function updateNodeApprovers(nodeId: number, userIds: number[]) {
  try {
    console.log(`正在更新节点ID=${nodeId}的审批人列表...`, userIds);
    const response = await api.put(`/workflow-nodes/${nodeId}/approvers`, { user_ids: userIds });
    return response.data;
  } catch (error) {
    console.error(`更新审批人列表失败:`, error);
    throw error;
  }
} 