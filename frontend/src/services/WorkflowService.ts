import * as workflowsAPI from '../api/workflows';
import * as workflowNodesAPI from '../api/workflow_nodes';
import * as templatesAPI from '../api/index';
import { Workflow, WorkflowCreate, WorkflowUpdate, WorkflowNode, WorkflowNodeCreate, User } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class WorkflowService {
  // 获取工作流列表
  static async getWorkflows(): Promise<Workflow[]> {
    try {
      const response = await workflowsAPI.getWorkflows();
      
      console.log('Workflows API 返回数据:', response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log('从分页数据中提取workflows数组');
        return response.items;
      }
      
      // 如果返回的是数组，直接返回
      if (Array.isArray(response)) {
        return response;
      }
      
      // 其他情况返回空数组
      console.error('API返回的workflows格式不正确:', response);
      return [];
    } catch (error) {
      console.error('获取工作流列表失败:', error);
      throw error;
    }
  }

  // 获取工作流详情
  static async getWorkflow(id: number): Promise<Workflow> {
    try {
      console.log(`开始获取工作流 ${id} 详情`);
      const workflow = await workflowsAPI.getWorkflow(id);
      
      // 确保工作流对象有效
      if (!workflow || !workflow.id) {
        throw new Error(`无效的工作流数据: ${JSON.stringify(workflow)}`);
      }
      
      // 获取工作流节点
      try {
        console.log(`获取工作流 ${id} 的节点`);
        // 使用单个节点获取函数来获取所有节点
        const nodes = await workflowsAPI.getWorkflowNode(id);
        workflow.nodes = nodes; // 将节点添加到工作流对象
        console.log(`工作流 ${id} 的节点数量: ${nodes.length}`);
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
  static async createWorkflow(workflow: WorkflowCreate): Promise<Workflow> {
    try {
      return await workflowsAPI.createWorkflow(workflow);
    } catch (error) {
      console.error('创建工作流失败:', error);
      throw error;
    }
  }

  // 更新工作流
  static async updateWorkflow(id: number, workflow: WorkflowUpdate): Promise<Workflow> {
    try {
      return await workflowsAPI.updateWorkflow(id, workflow);
    } catch (error) {
      console.error(`更新工作流 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除工作流
  static async deleteWorkflow(id: number): Promise<void> {
    try {
      await workflowsAPI.deleteWorkflow(id);
    } catch (error) {
      console.error(`删除工作流 ${id} 失败:`, error);
      throw error;
    }
  }

  // 获取模板列表
  static async getTemplates() {
    try {
      return await templatesAPI.default.templates.getTemplates();
    } catch (error) {
      console.error('获取模板列表失败:', error);
      throw error;
    }
  }

  // 获取角色列表
  static async getRoles() {
    try {
      return await templatesAPI.default.roles.getRoles();
    } catch (error) {
      console.error('获取角色列表失败:', error);
      throw error;
    }
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
  static addNode(nodes: WorkflowNodeCreate[]): WorkflowNodeCreate[] {
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
    const updatedNodes = [...nodes];
    
    // 获取当前节点
    const currentNode = updatedNodes[index];
    
    // 计算目标位置
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    // 检查目标位置是否有效
    if (targetIndex < 0 || targetIndex >= updatedNodes.length) {
      return updatedNodes;
    }
    
    // 交换节点位置
    updatedNodes[index] = updatedNodes[targetIndex];
    updatedNodes[targetIndex] = currentNode;
    
    // 更新排序
    updatedNodes.forEach((node, idx) => {
      node.order_index = idx;
    });
    
    return updatedNodes;
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
      case 'approver_user_id':
        node.approver_user_id = value as number | null;
        break;
      case 'multi_approve_type':
        node.multi_approve_type = value as string;
        break;
      case 'need_select_next_approver':
        node.need_select_next_approver = value as boolean;
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