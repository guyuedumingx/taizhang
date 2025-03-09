import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, Select, Switch, message } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { WorkflowNodeCreate, Template, User, Role } from '../../types';
import WorkflowNodeList from '../../components/workflow/WorkflowNodeList';
import { WorkflowService } from '../../services/WorkflowService';

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
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [nodes, setNodes] = useState<WorkflowNodeCreate[]>([]);
  const isEdit = !!id;

  // 检查权限并加载数据
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.WORKFLOW_EDIT : PERMISSIONS.WORKFLOW_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限访问此页面');
      navigate('/workflow');
      return;
    }

    const fetchData = async () => {
      try {
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
          await fetchWorkflow(parseInt(id));
        } else {
          // 创建模式，初始化节点
          setNodes(WorkflowService.initializeNodes());
        }
      } catch (error) {
        console.error('加载数据失败:', error);
        message.error('加载数据失败，请刷新页面重试');
      }
    };

    fetchData();
  }, [isEdit, id, hasPermission, navigate]);

  // 获取工作流详情
  const fetchWorkflow = async (workflowId: number) => {
    setLoading(true);
    try {
      const response = await WorkflowService.getWorkflow(workflowId);
      
      // 设置表单初始值
      form.setFieldsValue({
        name: response.name,
        description: response.description,
        template_id: response.template_id,
        is_active: response.is_active,
      });
      
      // 设置节点
      if (response.nodes && response.nodes.length > 0) {
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
        setNodes(WorkflowService.initializeNodes());
      }
    } catch (error) {
      console.error('获取工作流详情失败:', error);
      message.error('获取工作流详情失败');
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
      // 准备节点数据
      const formattedNodes = nodes.map((node, index) => ({
        ...node,
        order_index: index,
      }));
      
      // 准备工作流数据
      const workflowData = {
        ...values,
        nodes: formattedNodes,
      };
      
      if (isEdit && id) {
        // 更新工作流
        await WorkflowService.updateWorkflow(parseInt(id), workflowData);
        message.success('工作流更新成功');
      } else {
        // 创建工作流
        await WorkflowService.createWorkflow(workflowData);
        message.success('工作流创建成功');
      }
      
      // 返回工作流列表页面
      navigate('/workflow');
    } catch (error) {
      console.error('提交工作流失败:', error);
      message.error('提交工作流失败，请检查输入并重试');
    } finally {
      setLoading(false);
    }
  };

  return (
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
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            style={{ marginRight: 16 }}
          >
            {isEdit ? '更新工作流' : '创建工作流'}
          </Button>
          <Button onClick={() => navigate('/workflow')}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default WorkflowForm; 