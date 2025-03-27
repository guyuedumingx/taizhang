import * as workflowsApi from '../api/workflows';
import { Workflow, WorkflowCreate, WorkflowUpdate, WorkflowNode, WorkflowNodeCreate, LedgerApproval, Template, User, Role } from '../types';

// 定义查询参数类型
type QueryParams = Record<string, string | number | boolean | undefined>;

export class WorkflowService {
  // 获取工作流列表
  static async getWorkflows(params?: QueryParams): Promise<Workflow[]> {
    try {
      let response;
      if (params) {
        // 如果提供了参数，尝试使用api调用
        response = await workflowsApi.getWorkflows();
      } else {
        // 否则使用标准调用
        response = await workflowsApi.getWorkflows();
      }
      
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
      const workflow = await workflowsApi.getWorkflow(id);
      
      // 确保工作流对象有效
      if (!workflow || !workflow.id) {
        throw new Error(`无效的工作流数据: ${JSON.stringify(workflow)}`);
      }
      
      // 获取工作流节点
      try {
        console.log(`获取工作流 ${id} 的节点`);
        const nodes = await workflowsApi.getWorkflowNodes(id);
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
      return await workflowsApi.createWorkflow(workflow);
    } catch (error) {
      console.error('创建工作流失败:', error);
      throw error;
    }
  }

  // 更新工作流
  static async updateWorkflow(id: number, workflow: WorkflowUpdate): Promise<Workflow> {
    try {
      return await workflowsApi.updateWorkflow(id, workflow);
    } catch (error) {
      console.error(`更新工作流 ${id} 失败:`, error);
      throw error;
    }
  }

  // 删除工作流
  static async deleteWorkflow(id: number): Promise<void> {
    try {
      await workflowsApi.deleteWorkflow(id);
    } catch (error) {
      console.error(`删除工作流 ${id} 失败:`, error);
      throw error;
    }
  }

  // 获取模板列表
  static async getTemplates(): Promise<Template[]> {
    try {
      return await workflowsApi.getTemplates();
    } catch (error) {
      console.error('获取模板列表失败:', error);
      throw error;
    }
  }

  // 获取角色列表
  static async getRoles(): Promise<Role[]> {
    try {
      return await workflowsApi.getRoles();
    } catch (error) {
      console.error('获取角色列表失败:', error);
      throw error;
    }
  }

  // 获取用户列表
  static async getUsers(): Promise<User[]> {
    try {
      return await workflowsApi.getUsers();
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
    // 不允许删除开始和结束节点
    if (nodes[index].node_type === 'start' || nodes[index].node_type === 'end') {
      throw new Error('不能删除开始或结束节点');
    }
    
    const updatedNodes = [...nodes];
    updatedNodes.splice(index, 1);
    
    // 更新剩余节点的顺序
    updatedNodes.forEach((node, i) => {
      node.order_index = i;
    });
    
    return updatedNodes;
  }

  // 移动节点
  static moveNode(nodes: WorkflowNodeCreate[], index: number, direction: 'up' | 'down'): WorkflowNodeCreate[] {
    // 不允许移动开始和结束节点
    if (nodes[index].node_type === 'start' || nodes[index].node_type === 'end') {
      throw new Error('不能移动开始或结束节点');
    }
    
    // 不允许将节点移到开始节点之前或结束节点之后
    if (
      (direction === 'up' && index === 1) || // 第二个节点（开始节点后面的第一个节点）
      (direction === 'down' && index === nodes.length - 2) // 倒数第二个节点（结束节点前面的节点）
    ) {
      throw new Error('不能将节点移到开始节点之前或结束节点之后');
    }
    
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    const updatedNodes = [...nodes];
    
    // 交换节点
    [updatedNodes[index], updatedNodes[newIndex]] = [updatedNodes[newIndex], updatedNodes[index]];
    
    // 更新顺序
    updatedNodes.forEach((node, i) => {
      node.order_index = i;
    });
    
    return updatedNodes;
  }

  // 更新节点
  static updateNode(
    nodes: WorkflowNodeCreate[], 
    index: number, 
    field: string, 
    value: unknown
  ): WorkflowNodeCreate[] {
    const updatedNodes = [...nodes];
    const node = updatedNodes[index];
    
    // 根据字段名称更新相应的属性
    switch (field) {
      case 'name':
        node.name = value as string;
        break;
      case 'description':
        node.description = value as string;
        break;
      case 'node_type':
        node.node_type = value as string;
        break;
      case 'approver_role_id':
        node.approver_role_id = value as number | null;
        break;
      case 'approver_user_id':
        node.approver_user_id = value as number | null;
        break;
      case 'is_final':
        node.is_final = value as boolean | undefined;
        break;
      case 'multi_approve_type':
        node.multi_approve_type = value as string;
        break;
      case 'need_select_next_approver':
        node.need_select_next_approver = value as boolean;
        break;
      case 'approver_ids':
        node.approver_ids = value as number[];
        break;
      case 'reject_to_node_id':
        node.reject_to_node_id = value as number | null | undefined;
        break;
      // 可以根据需要添加更多字段
    }
    
    return updatedNodes;
  }

  // 获取工作流节点
  static async getWorkflowNodes(workflowId: number): Promise<WorkflowNode[]> {
    try {
      return await workflowsApi.getWorkflowNodes(workflowId);
    } catch (error) {
      console.error(`获取工作流 ${workflowId} 节点失败:`, error);
      throw error;
    }
  }
  
  // 创建工作流节点
  static async createWorkflowNode(workflowId: number, node: WorkflowNodeCreate): Promise<WorkflowNode> {
    try {
      return await workflowsApi.createWorkflowNode(workflowId, node);
    } catch (error) {
      console.error(`创建工作流 ${workflowId} 节点失败:`, error);
      throw error;
    }
  }
  
  // 删除工作流节点
  static async deleteWorkflowNode(workflowId: number, nodeId: number): Promise<void> {
    try {
      await workflowsApi.deleteWorkflowNode(workflowId, nodeId);
    } catch (error) {
      console.error(`删除工作流节点 ${nodeId} 失败:`, error);
      throw error;
    }
  }

  // 处理审批
  static async processApproval(ledgerId: number, data: LedgerApproval): Promise<void> {
    try {
      await workflowsApi.processApproval(ledgerId, data);
    } catch (error) {
      console.error(`处理台账 ${ledgerId} 审批失败:`, error);
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
      await workflowsApi.updateNodeApprovers(nodeId, approverIds);
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
      const response = await workflowsApi.getNodeApprovers(nodeId);
      console.log(`获取节点ID=${nodeId}的审批人返回数据:`, response);
      
      // 处理分页格式的数据 {items: Array, total: number, page: number, size: number}
      if (response && typeof response === 'object' && 'items' in response && Array.isArray(response.items)) {
        console.log(`从分页数据中提取节点ID=${nodeId}的审批人数组`);
        return response.items;
      }
      
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