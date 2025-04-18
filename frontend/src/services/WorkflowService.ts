import * as workflowsAPI from '../api/workflows';
import * as workflowNodesAPI from '../api/workflow_nodes';
import * as templatesAPI from '../api/index';
import { Workflow, WorkflowCreate, WorkflowUpdate, WorkflowNode, WorkflowNodeCreate, User } from '../types';

export class WorkflowService {
  // 获取工作流列表
  static async getWorkflows(): Promise<Workflow[]> {
      return await workflowsAPI.getWorkflows();
  }

  // 获取工作流详情
  static async getWorkflow(id: number): Promise<Workflow> {
    return await workflowsAPI.getWorkflow(id);
  }

  // 创建工作流
  static async createWorkflow(workflow: WorkflowCreate): Promise<Workflow> {
    return await workflowsAPI.createWorkflow(workflow);
  }

  // 更新工作流
  static async updateWorkflow(id: number, workflow: WorkflowUpdate): Promise<Workflow> {
    return await workflowsAPI.updateWorkflow(id, workflow);
  }

  // 删除工作流
  static async deleteWorkflow(id: number): Promise<void> {
    return await workflowsAPI.deleteWorkflow(id);
  }

  // 获取角色列表
  static async getRoles() {
    return await templatesAPI.default.roles.getRoles();
  }

  // 获取用户列表
  static async getUsers() {
    try {
      return await templatesAPI.default.users.getUsers();
    } catch (error) {
      console.error('获取用户列表失败:', error);
      throw error;
    }
  }

  // 初始化节点
  static initializeNodes(): WorkflowNodeCreate[] {
    return workflowsAPI.initializeNodes();
  }

  // 添加节点
  static addNode(nodes: WorkflowNodeCreate[]): WorkflowNodeCreate[] {
    const updatedNodes = [...nodes];
    const newNode: WorkflowNodeCreate = {
      workflow_id: 0,
      name: `审批节点 ${nodes.length}`,
      description: '审批',
      node_type: 'approval',
      approver_role_id: null,
      order_index: nodes.length - 1, // 插入到结束节点之前
      is_final: false,
      multi_approve_type: 'any',
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
  static removeNode(nodes: WorkflowNodeCreate[], index: number): WorkflowNodeCreate[] {
    const updatedNodes = [...nodes];
    updatedNodes.splice(index, 1);
    
    // 更新所有节点的排序
    updatedNodes.forEach((node, idx) => {
      node.order_index = idx;
    });
    
    return updatedNodes;
  }

  // 移动节点
  static moveNode(nodes: WorkflowNodeCreate[], index: number, direction: 'up' | 'down'): WorkflowNodeCreate[] {
    return workflowsAPI.moveNode(nodes, index, direction);
  }

  // 更新节点字段
  static updateNode(
    nodes: WorkflowNodeCreate[], 
    index: number, 
    field: string, 
    value: unknown
  ): WorkflowNodeCreate[] {
    const updatedNodes = [...nodes];
    
    // 检查索引是否有效
    if (index < 0 || index >= updatedNodes.length) {
      return updatedNodes;
    }
    
    // 创建节点的副本
    const node = { ...updatedNodes[index] };
    
    // 根据字段更新节点
    switch (field) {
      case 'name':
        node.name = value as string;
        break;
      case 'description':
        node.description = value as string;
        break;
      case 'approver_role_id':
        node.approver_role_id = value as number | null;
        break;
      case 'multi_approve_type':
        node.multi_approve_type = value as string;
        break;
      case 'reject_to_node_id':
        node.reject_to_node_id = value as number | null;
        break;
      case 'approver_ids':
        node.approver_ids = value as number[];
        break;
      default:
        console.warn(`未知的字段: ${field}`);
        break;
    }
    
    // 更新节点
    updatedNodes[index] = node;
    
    return updatedNodes;
  }
  
  // 获取工作流节点
  static async getWorkflowNodes(workflowId: number): Promise<WorkflowNode[]> {
    try {
      return await workflowsAPI.getWorkflowNode(workflowId);
    } catch (error) {
      console.error(`获取工作流 ${workflowId} 节点失败:`, error);
      throw error;
    }
  }

  // 保存工作流节点的审批人
  static async saveNodeApprovers(nodeId: number, approverIds: number[]): Promise<void> {
    try {
      console.log(`正在保存节点ID=${nodeId}的审批人列表:`, approverIds);
      
      if (!nodeId || nodeId <= 0) {
        console.warn('节点ID无效，跳过保存审批人');
        return;
      }
      
      // 使用更新API直接设置全部审批人
      await workflowNodesAPI.updateNodeApprovers(nodeId, approverIds);
      console.log(`保存节点ID=${nodeId}的审批人列表成功`);
    } catch (error) {
      console.error(`保存节点ID=${nodeId}的审批人列表失败:`, error);
      throw error;
    }
  }

  // 获取工作流节点的审批人
  static async getNodeApprovers(nodeId: number): Promise<User[]> {
    try {
      console.log(`获取节点ID=${nodeId}的审批人`);
      const response = await workflowNodesAPI.getNodeApprovers(nodeId);
      console.log(`获取节点ID=${nodeId}的审批人返回数据:`, response);
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error(`获取节点ID=${nodeId}的审批人返回格式不正确:`, response);
      return [];
    } catch (error) {
      console.error(`获取节点ID=${nodeId}的审批人失败:`, error);
      return [];
    }
  }
} 