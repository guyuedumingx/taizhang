import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, Select, Switch, message } from 'antd';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { WorkflowNodeCreate, Template, User, Role } from '../../types';
import WorkflowNodeList from '../../components/workflow/WorkflowNodeList';
import { WorkflowService } from '../../services/WorkflowService';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface FormValues {
  name: string;
  description: string;
  template_id: number;
  is_active: boolean;
}

const WorkflowForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [nodes, setNodes] = useState<WorkflowNodeCreate[]>([]);
  const isEdit = !!id;
  
  // 从URL查询参数中获取模板ID
  const queryParams = new URLSearchParams(location.search);
  const templateId = queryParams.get('template_id');

  // 检查权限并加载数据
  useEffect(() => {
    console.log('WorkflowForm useEffect triggered, id:', id);
    
    const requiredPermission = isEdit ? PERMISSIONS.WORKFLOW_EDIT : PERMISSIONS.WORKFLOW_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限访问此页面');
      navigate('/dashboard/workflow');
      return;
    }

    const fetchData = async () => {
      try {
        console.log('Fetching data for workflow, isEdit:', isEdit);
        const [templatesData, rolesData, usersData] = await Promise.all([
          WorkflowService.getTemplates(),
          WorkflowService.getRoles(),
          WorkflowService.getUsers()
        ]);
        
        setTemplates(templatesData);
        setRoles(rolesData);
        setUsers(usersData);
        
        // 如果是编辑模式，获取工作流详情
        if (isEdit && id) {
          console.log('Fetching workflow details for id:', id);
          try {
            await fetchWorkflow(parseInt(id, 10));
          } catch (error) {
            console.error('获取工作流详情失败:', error);
            message.error('获取工作流详情失败，请返回列表页重试');
            navigate('/dashboard/workflow');
          }
        } else {
          // 创建模式，初始化节点
          console.log('Initializing nodes for new workflow');
          setNodes(WorkflowService.initializeNodes());
          
          // 如果有模板ID参数，预先选择该模板
          if (templateId) {
            console.log('Setting template ID from URL parameter:', templateId);
            form.setFieldsValue({
              template_id: parseInt(templateId, 10)
            });
          }
        }
      } catch (error) {
        console.error('加载数据失败:', error);
        message.error('加载数据失败，请刷新页面重试');
      }
    };

    fetchData();
  }, [isEdit, id, templateId, hasPermission, navigate, form]);

  // 获取工作流详情
  const fetchWorkflow = async (workflowId: number) => {
    console.log('fetchWorkflow called with id:', workflowId);
    setLoading(true);
    try {
      const response = await WorkflowService.getWorkflow(workflowId);
      console.log('Workflow data received:', response);
      
      if (!response || !response.id) {
        throw new Error('无效的工作流数据');
      }
      
      // 设置表单初始值
      form.setFieldsValue({
        name: response.name,
        description: response.description,
        template_id: response.template_id,
        is_active: response.is_active,
      });
      
      // 设置节点
      if (response.nodes && response.nodes.length > 0) {
        console.log('Setting nodes from response:', response.nodes);
        const formattedNodes = response.nodes.map(node => ({
          workflow_id: node.workflow_id,
          name: node.name,
          description: node.description,
          node_type: node.node_type,
          approver_role_id: node.approver_role_id,
          approver_user_id: node.approver_user_id,
          order_index: node.order_index,
          is_final: node.is_final,
          reject_to_node_id: node.reject_to_node_id,
        }));
        setNodes(formattedNodes);
      } else {
        console.log('No nodes in response, initializing default nodes');
        setNodes(WorkflowService.initializeNodes());
      }
    } catch (error) {
      console.error('获取工作流详情失败:', error);
      message.error('获取工作流详情失败');
      throw error; // 重新抛出错误，让调用者处理
    } finally {
      setLoading(false);
    }
  };

  // 添加节点
  const handleAddNode = () => {
    try {
      setNodes(WorkflowService.addNode(nodes));
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('添加节点失败');
      }
    }
  };

  // 删除节点
  const handleDeleteNode = (index: number) => {
    try {
      setNodes(WorkflowService.removeNode(nodes, index));
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('删除节点失败');
      }
    }
  };

  // 移动节点
  const handleMoveNode = (index: number, direction: 'up' | 'down') => {
    try {
      setNodes(WorkflowService.moveNode(nodes, index, direction));
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('移动节点失败');
      }
    }
  };

  // 更新节点属性
  const handleUpdateNode = (index: number, field: string, value: unknown) => {
    try {
      setNodes(WorkflowService.updateNode(nodes, index, field, value));
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('更新节点失败');
      }
    }
  };

  // 提交表单
  const handleSubmit = async (values: FormValues) => {
    setLoading(true);
    try {
      console.log('提交表单数据:', values);
      console.log('节点数据:', nodes);
      
      // 准备节点数据
      const formattedNodes = nodes.map((node, index) => ({
        ...node,
        order_index: index,
      }));
      
      if (isEdit && id) {
        console.log(`更新工作流 ID: ${id}`);
        // 更新工作流基本信息
        const workflowUpdateData = {
          name: values.name,
          description: values.description,
          is_active: values.is_active
        };
        
        await WorkflowService.updateWorkflow(parseInt(id), workflowUpdateData);
        message.success('工作流基本信息更新成功');
        
        // 获取已有节点
        try {
          const existingNodes = await WorkflowService.getWorkflowNodes(parseInt(id));
          console.log(`获取到 ${existingNodes.length} 个现有节点`);
          
          // 删除所有已有节点
          await Promise.all(
            existingNodes.map(node => WorkflowService.deleteWorkflowNode(parseInt(id), node.id))
          );
          console.log('已删除所有现有节点');
        } catch (error) {
          console.error('删除现有节点失败:', error);
        }
        
        // 创建新节点
        try {
          const nodesWithWorkflowId = formattedNodes.map(node => ({
            ...node,
            workflow_id: parseInt(id)
          }));
          
          console.log(`准备创建 ${nodesWithWorkflowId.length} 个新节点`);
          await Promise.all(
            nodesWithWorkflowId.map(node => WorkflowService.createWorkflowNode(parseInt(id), node))
          );
          console.log('所有节点创建成功');
          message.success('工作流节点更新成功');
        } catch (error) {
          console.error('创建节点失败:', error);
          message.error('创建节点失败，请检查节点配置');
        }
      } else {
        console.log('创建新工作流');
        // 创建新工作流
        const workflowCreateData = {
          ...values,
          nodes: formattedNodes
        };
        
        await WorkflowService.createWorkflow(workflowCreateData);
        message.success('工作流创建成功');
      }
      
      // 返回工作流列表页面
      console.log('操作完成，返回工作流列表页面');
      navigate('/dashboard/workflow');
    } catch (error) {
      console.error('提交工作流失败:', error);
      message.error('提交工作流失败，请检查输入并重试');
    } finally {
      setLoading(false);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    navigate('/dashboard/workflow');
  };

  return (
    <>
      <BreadcrumbNav 
        items={[
          ...(templateId ? [{ title: '模板管理', path: '/dashboard/templates' }] : []),
          { title: '工作流管理', path: '/dashboard/workflow' },
          { title: isEdit ? '编辑工作流' : '创建工作流' }
        ]}
        backButtonText="返回"
        onBack={() => templateId 
          ? navigate(`/dashboard/workflow?template_id=${templateId}`) 
          : navigate('/dashboard/workflow')
        }
      />
      
      <Card 
        title={
          <Title level={3}>
            {isEdit ? '编辑工作流' : '创建工作流'}
          </Title>
        }
        bordered={false}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            is_active: true,
          }}
        >
          <Form.Item
            name="name"
            label="工作流名称"
            rules={[
              { required: true, message: '请输入工作流名称' },
              { max: 50, message: '工作流名称不能超过50个字符' },
            ]}
          >
            <Input placeholder="请输入工作流名称" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="工作流描述"
            rules={[
              { max: 200, message: '工作流描述不能超过200个字符' },
            ]}
          >
            <TextArea 
              placeholder="请输入工作流描述" 
              rows={3}
              maxLength={200}
              showCount
            />
          </Form.Item>
          
          <Form.Item
            name="template_id"
            label="关联模板"
            rules={[
              { required: true, message: '请选择关联的模板' },
            ]}
          >
            <Select placeholder="请选择模板">
              {templates.map(template => (
                <Option key={template.id} value={template.id}>
                  {template.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="is_active"
            label="是否启用"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          
          {/* 工作流节点列表 */}
          <WorkflowNodeList
            nodes={nodes}
            roles={roles}
            users={users}
            onAddNode={handleAddNode}
            onDeleteNode={handleDeleteNode}
            onMoveNode={handleMoveNode}
            onUpdateNode={handleUpdateNode}
          />
          
          <Form.Item style={{ marginTop: 24 }}>
            <Button type="primary" htmlType="submit" loading={loading} style={{ marginRight: 16 }}>
              {isEdit ? '更新工作流' : '创建工作流'}
            </Button>
            <Button onClick={handleCancel}>
              取消
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </>
  );
};

export default WorkflowForm; 