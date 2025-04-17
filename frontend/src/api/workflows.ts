import { API_BASE_URL } from '../config';
import { api } from './index';
import { 
  Workflow, 
  WorkflowCreate, 
  WorkflowUpdate, 
  WorkflowNode,
  WorkflowNodeCreate,
  WorkflowNodeUpdate,
  User
} from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

// ----------------- 工作流管理API -----------------

// 获取工作流列表
export async function getWorkflows(params?: QueryParams): Promise<Workflow[]> {
  try {
    const response = await api.get('/workflows/', { params });
    
    console.log('Workflows API 返回数据:', response.data);
    
    // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
    if (response.data && typeof response.data === 'object' && 'items' in response.data && Array.isArray(response.data.items)) {
      console.log('从分页数据中提取workflows数组');
      return response.data.items;
    }
    
    // 如果返回的是数组，直接返回
    if (Array.isArray(response.data)) {
      return response.data;
    }
    
    // 其他情况返回空数组
    console.error('API返回的workflows格式不正确:', response.data);
    return [];
  } catch (error) {
    console.error('获取工作流列表失败:', error);
    throw error;
  }
}

// 获取工作流详情
export async function getWorkflow(id: number): Promise<Workflow> {
  try {
    console.log(`开始获取工作流 ${id} 详情`);
    const response = await api.get(`/workflows/${id}`);
    const workflow = response.data;
    
    // 确保工作流对象有效
    if (!workflow || !workflow.id) {
      throw new Error(`无效的工作流数据: ${JSON.stringify(workflow)}`);
    }
    
    // 获取工作流节点
    try {
      console.log(`获取工作流 ${id} 的节点`);
      if (workflow.nodes && workflow.nodes.length > 0) {
        // 使用 Promise.all 并行获取所有节点的详细信息
        const nodePromises = workflow.nodes.map((node: WorkflowNode) => 
          getWorkflowNode(node.id)
        );
        workflow.nodes = await Promise.all(nodePromises);
        console.log(`工作流 ${id} 的节点数量: ${workflow.nodes.length}`);
      } else {
        workflow.nodes = []; // 如果没有节点，设置为空数组
      }
    } catch (nodeError) {
      console.error(`获取工作流 ${id} 节点失败:`, nodeError);
      workflow.nodes = []; // 设置为空数组，避免undefined错误
    }
    
    console.log(`成功获取工作流 ${id} 详情:`, workflow);
    return workflow;
  } catch (error) {
    console.error(`获取工作流 ${id} 详情失败:`, error);
    throw error;
  }
}

// 创建工作流
export async function createWorkflow(workflow: WorkflowCreate): Promise<Workflow> {
  try {
    const response = await api.post('/workflows/', workflow);
    return response.data;
  } catch (error) {
    console.error('创建工作流失败:', error);
    throw error;
  }
}

// 更新工作流
export async function updateWorkflow(id: number, workflow: WorkflowUpdate): Promise<Workflow> {
  try {
    const response = await api.put(`/workflows/${id}`, workflow);
    return response.data;
  } catch (error) {
    console.error(`更新工作流 ${id} 失败:`, error);
    throw error;
  }
}

// 删除工作流
export async function deleteWorkflow(id: number): Promise<void> {
  try {
    await api.delete(`/workflows/${id}`);
  } catch (error) {
    console.error(`删除工作流 ${id} 失败:`, error);
    throw error;
  }
}

// 获取工作流节点详情
export async function getWorkflowNode(id: number): Promise<WorkflowNode> {
  try {
    const response = await api.get(`/workflow-nodes/${id}`);
    return response.data;
  } catch (error) {
    console.error(`获取工作流节点 ${id} 失败:`, error);
    throw error;
  }
}

// 获取工作流节点列表
export async function getWorkflowNodes(workflowId: number): Promise<WorkflowNode[]> {
  try {
    const response = await api.get(`/workflows/${workflowId}/nodes`);
    return response.data;
  } catch (error) {
    console.error(`获取工作流 ${workflowId} 节点列表失败:`, error);
    throw error;
  }
}

// 创建工作流节点
export async function createWorkflowNode(node: WorkflowNodeCreate): Promise<WorkflowNode> {
  try {
    const response = await api.post('/workflow-nodes/', node);
    return response.data;
  } catch (error) {
    console.error('创建工作流节点失败:', error);
    throw error;
  }
}

// 更新工作流节点
export async function updateWorkflowNode(id: number, node: WorkflowNodeUpdate): Promise<WorkflowNode> {
  try {
    const response = await api.put(`/workflow-nodes/${id}`, node);
    return response.data;
  } catch (error) {
    console.error(`更新工作流节点 ${id} 失败:`, error);
    throw error;
  }
}

// 删除工作流节点
export async function deleteWorkflowNode(id: number): Promise<void> {
  try {
    await api.delete(`/workflow-nodes/${id}`);
  } catch (error) {
    console.error(`删除工作流节点 ${id} 失败:`, error);
    throw error;
  }
}

// 设置节点审批人
export async function saveNodeApprovers(nodeId: number, approverIds: number[]): Promise<void> {
  try {
    await api.post(`/workflow-nodes/${nodeId}/approvers`, { approver_ids: approverIds });
  } catch (error) {
    console.error(`设置节点 ${nodeId} 审批人失败:`, error);
    throw error;
  }
}

// 获取节点审批人
export async function getNodeApprovers(nodeId: number): Promise<User[]> {
  try {
    const response = await api.get(`/workflow-nodes/${nodeId}/approvers`);
    return response.data;
  } catch (error) {
    console.error(`获取节点 ${nodeId} 审批人失败:`, error);
    throw error;
  }
}

// 初始化节点
export function initializeNodes(): WorkflowNodeCreate[] {
  return [
    {
      workflow_id: 0, // 临时值，提交时会被替换
      name: '开始',
      description: '工作流开始',
      node_type: 'start',
      order_index: 0,
      multi_approve_type: 'any',
      need_select_next_approver: false,
      approver_ids: [],
    },
    {
      workflow_id: 0,
      name: '审批',
      description: '主管审批',
      node_type: 'approval',
      approver_role_id: null,
      approver_user_id: null,
      order_index: 1,
      multi_approve_type: 'any',
      need_select_next_approver: false,
      approver_ids: [],
    },
    {
      workflow_id: 0,
      name: '结束',
      description: '工作流结束',
      node_type: 'end',
      order_index: 2,
      is_final: true,
      multi_approve_type: 'any',
      need_select_next_approver: false,
      approver_ids: [],
    },
  ];
}

// 添加节点
export function addNode(nodes: WorkflowNodeCreate[]): WorkflowNodeCreate[] {
  const updatedNodes = [...nodes];
  const newNode: WorkflowNodeCreate = {
    workflow_id: 0,
    name: `审批节点 ${nodes.length}`,
    description: '审批',
    node_type: 'approval',
    approver_role_id: null,
    approver_user_id: null,
    order_index: nodes.length - 1, // 插入到结束节点之前
    is_final: false,
    multi_approve_type: 'any',
    need_select_next_approver: false,
    approver_ids: [],
  };
  
  // 更新结束节点的顺序
  const endNodeIndex = updatedNodes.findIndex(node => node.node_type === 'end');
  if (endNodeIndex !== -1) {
    updatedNodes[endNodeIndex].order_index = nodes.length;
  }
  
  // 插入新节点到结束节点之前
  updatedNodes.splice(endNodeIndex, 0, newNode);
  
  return updatedNodes;
}

// 删除节点
export function removeNode(nodes: WorkflowNodeCreate[], index: number): WorkflowNodeCreate[] {
  const updatedNodes = [...nodes];
  
  // 检查不是开始和结束节点
  if (updatedNodes[index].node_type === 'start' || updatedNodes[index].node_type === 'end') {
    return updatedNodes;
  }
  
  // 删除节点
  updatedNodes.splice(index, 1);
  
  // 重新排序
  return updatedNodes.map((node, i) => ({ ...node, order_index: i }));
}

// 移动节点
export function moveNode(nodes: WorkflowNodeCreate[], index: number, direction: 'up' | 'down'): WorkflowNodeCreate[] {
  const updatedNodes = [...nodes];
  
  // 不能移动开始和结束节点
  if (updatedNodes[index].node_type === 'start' || updatedNodes[index].node_type === 'end') {
    return updatedNodes;
  }
  
  // 计算新的索引
  const newIndex = direction === 'up' ? index - 1 : index + 1;
  
  // 边界检查
  if (newIndex < 1 || newIndex >= updatedNodes.length - 1) {
    return updatedNodes;
  }
  
  // 交换节点
  const temp = updatedNodes[index];
  updatedNodes[index] = updatedNodes[newIndex];
  updatedNodes[newIndex] = temp;
  
  // 更新 order_index
  return updatedNodes.map((node, i) => ({ ...node, order_index: i }));
}

// 更新节点字段
export function updateNode(
  nodes: WorkflowNodeCreate[], 
  index: number, 
  field: string, 
  value: unknown
): WorkflowNodeCreate[] {
  const updatedNodes = [...nodes];
  
  // 检查索引有效
  if (index < 0 || index >= updatedNodes.length) {
    return updatedNodes;
  }
  
  // 处理特殊字段
  if (field === 'approver_ids' && Array.isArray(value)) {
    // 更新审批人ID列表
    updatedNodes[index] = {
      ...updatedNodes[index],
      approver_ids: value,
    };
  } else if (field === 'approver_role_id') {
    // 更新审批角色ID
    updatedNodes[index] = {
      ...updatedNodes[index],
      approver_role_id: value as number | null,
      // 如果设置了角色，清除用户
      approver_user_id: value ? null : updatedNodes[index].approver_user_id,
    };
  } else if (field === 'approver_user_id') {
    // 更新审批用户ID
    updatedNodes[index] = {
      ...updatedNodes[index],
      approver_user_id: value as number | null,
      // 如果设置了用户，清除角色
      approver_role_id: value ? null : updatedNodes[index].approver_role_id,
    };
  } else if (field === 'multi_approve_type') {
    // 更新多人审批类型
    updatedNodes[index] = {
      ...updatedNodes[index],
      multi_approve_type: value as string,
    };
  } else if (field === 'need_select_next_approver') {
    // 更新是否需要选择下一个审批人
    updatedNodes[index] = {
      ...updatedNodes[index],
      need_select_next_approver: value as boolean,
    };
  } else {
    // 更新其他字段
    updatedNodes[index] = {
      ...updatedNodes[index],
      [field]: value,
    };
  }
  
  return updatedNodes;
}