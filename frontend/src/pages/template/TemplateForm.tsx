import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, Select, message, Divider, Space } from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { TemplateService } from '../../services/TemplateService';
import { TeamService } from '../../services/TeamService';
import { WorkflowService } from '../../services/WorkflowService';
import { TemplateCreate, TemplateUpdate, FieldCreate, Team, Workflow } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const TemplateForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [teams, setTeams] = useState<Team[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  
  const isEdit = !!id;

  // 检查权限并加载数据
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.TEMPLATE_EDIT : PERMISSIONS.TEMPLATE_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限执行此操作');
      navigate('/dashboard/templates');
      return;
    }

    // 获取团队列表
    fetchTeams();
    
    // 获取工作流列表
    fetchWorkflows();

    if (isEdit) {
      fetchTemplate(parseInt(id));
    }
  }, [isEdit, id, hasPermission, navigate]);

  // 获取团队列表
  const fetchTeams = async () => {
    try {
      const teamsData = await TeamService.getTeams();
      setTeams(teamsData);
    } catch (error) {
      console.error('获取团队列表失败:', error);
      message.error('获取团队列表失败');
    }
  };
  
  // 获取工作流列表
  const fetchWorkflows = async () => {
    try {
      const workflowsData = await WorkflowService.getWorkflows();
      const activeWorkflows = workflowsData.filter(workflow => workflow.is_active);
      setWorkflows(activeWorkflows);
    } catch (error) {
      console.error('获取工作流列表失败:', error);
      message.error('获取工作流列表失败');
    }
  };

  // 获取模板详情
  const fetchTemplate = async (templateId: number) => {
    setLoading(true);
    try {
      const template = await TemplateService.getTemplateDetail(templateId);
      
      // 转换字段数据格式以适应表单
      const fieldsData = template.fields.map(field => ({
        name: field.name,
        label: field.label || field.name,
        type: field.type,
        required: field.required,
        options: field.options ? field.options.join(',') : '',
        is_key_field: field.is_key_field || false
      }));
      
      // 设置表单初始值
      form.setFieldsValue({
        name: template.name,
        department: template.department,
        description: template.description || '',
        default_ledger_name: template.default_ledger_name || '',
        default_description: template.default_description || '',
        default_status: template.default_status || 'draft',
        default_team_id: template.default_team_id || null,
        default_workflow_id: template.default_workflow_id || null,
        fields: fieldsData
      });
    } catch (error) {
      console.error('获取模板详情失败:', error);
      message.error('获取模板详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 提交表单
  const handleSubmit = async (values: Record<string, unknown>) => {
    // 转换字段数据
    const fields = (values.fields as Array<Record<string, unknown>>).map((field) => {
      const fieldData: FieldCreate = {
        name: field.name as string,
        label: field.label as string,
        type: field.type as string,
        required: field.required as boolean || false,
        is_key_field: field.is_key_field as boolean || false
      };
      
      // 处理选项类型的字段
      if (field.type === 'select' || field.type === 'radio' || field.type === 'checkbox') {
        fieldData.options = field.options ? (field.options as string).split(',').map((opt: string) => opt.trim()) : [];
      }
      
      return fieldData;
    });
    
    setSubmitting(true);
    
    try {
      if (isEdit) {
        // 更新模板
        const updateData: TemplateUpdate = {
          name: values.name as string,
          department: values.department as string,
          description: values.description as string,
          default_ledger_name: values.default_ledger_name as string,
          default_description: values.default_description as string,
          default_status: values.default_status as string,
          default_team_id: values.default_team_id as number,
          default_workflow_id: values.default_workflow_id as number,
          fields: fields
        };
        
        await TemplateService.updateTemplate(parseInt(id), updateData);
        message.success('模板更新成功');
      } else {
        // 创建模板
        const createData: TemplateCreate = {
          name: values.name as string,
          department: values.department as string,
          description: values.description as string,
          default_ledger_name: values.default_ledger_name as string,
          default_description: values.default_description as string,
          default_status: values.default_status as string,
          default_team_id: values.default_team_id as number,
          default_workflow_id: values.default_workflow_id as number,
          fields: fields
        };
        
        await TemplateService.createTemplate(createData);
        message.success('模板创建成功');
      }
      
      // 返回模板列表页面
      navigate('/dashboard/templates');
    } catch (error) {
      console.error('模板操作失败:', error);
      message.error('操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '模板管理', path: '/dashboard/templates' },
          { title: isEdit ? '编辑模板' : '创建模板' }
        ]}
        backButtonText="返回列表"
        onBack={() => navigate('/dashboard/templates')}
      />
      
      <Card loading={loading}>
        <Title level={4}>{isEdit ? '编辑模板' : '创建模板'}</Title>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            default_status: 'draft',
            fields: []
          }}
        >
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>
          
          <Form.Item
            name="department"
            label="所属部门"
            rules={[{ required: true, message: '请选择所属部门' }]}
          >
            <Select placeholder="选择部门">
              <Option value="财务部">财务部</Option>
              <Option value="生产部">生产部</Option>
              <Option value="客服部">客服部</Option>
              <Option value="设备部">设备部</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="description"
            label="模板描述"
          >
            <TextArea rows={4} placeholder="请输入模板描述" />
          </Form.Item>
          
          <Divider orientation="left">台账默认值设置</Divider>
          
          <Form.Item
            name="default_ledger_name"
            label="默认台账名称"
          >
            <Input placeholder="请输入默认台账名称" />
          </Form.Item>
          
          <Form.Item
            name="default_description"
            label="默认台账描述"
          >
            <TextArea rows={2} placeholder="请输入默认台账描述" />
          </Form.Item>
          
          <Form.Item
            name="default_status"
            label="默认台账状态"
          >
            <Select placeholder="选择默认状态">
              <Option value="draft">草稿</Option>
              <Option value="active">处理中</Option>
              <Option value="completed">已完成</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="default_team_id"
            label="默认所属团队"
          >
            <Select placeholder="选择默认团队" allowClear>
              {teams.map(team => (
                <Option key={team.id} value={team.id}>{team.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="default_workflow_id"
            label="默认工作流"
          >
            <Select placeholder="选择默认工作流" allowClear>
              {workflows.map(workflow => (
                <Option key={workflow.id} value={workflow.id}>{workflow.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Divider orientation="left">字段配置</Divider>
          
          <Form.List
            name="fields"
            rules={[
              {
                validator: async (_, fields) => {
                  if (!fields || fields.length < 1) {
                    return Promise.reject(new Error('至少添加一个字段'));
                  }
                  return Promise.resolve();
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <>
                {fields.map((field) => (
                  <Card
                    key={field.key.toString()}
                    size="small"
                    title={`字段 ${field.name + 1}`}
                    style={{ marginBottom: 16 }}
                    extra={
                      fields.length > 1 ? (
                        <MinusCircleOutlined
                          onClick={() => remove(field.name)}
                        />
                      ) : null
                    }
                  >
                    <Form.Item
                      {...field}
                      name={[field.name, 'name']}
                      fieldKey={[field.key, 'name']}
                      label="字段名称"
                      rules={[{ required: true, message: '请输入字段名称' }]}
                    >
                      <Input placeholder="请输入字段名称" />
                    </Form.Item>
                    
                    <Form.Item
                      {...field}
                      name={[field.name, 'label']}
                      fieldKey={[field.key, 'label']}
                      label="显示名称"
                      rules={[{ required: true, message: '请输入显示名称' }]}
                    >
                      <Input placeholder="请输入显示名称" />
                    </Form.Item>
                    
                    <Form.Item
                      {...field}
                      name={[field.name, 'type']}
                      fieldKey={[field.key, 'type']}
                      label="字段类型"
                      rules={[{ required: true, message: '请选择字段类型' }]}
                    >
                      <Select placeholder="选择字段类型">
                        <Option value="input">单行文本</Option>
                        <Option value="textarea">多行文本</Option>
                        <Option value="number">数字</Option>
                        <Option value="select">下拉选择</Option>
                        <Option value="radio">单选</Option>
                        <Option value="checkbox">多选</Option>
                        <Option value="date">日期</Option>
                        <Option value="datetime">日期时间</Option>
                      </Select>
                    </Form.Item>
                    
                    <Form.Item
                      noStyle
                      shouldUpdate={(prevValues, currentValues) => {
                        return prevValues.fields[field.name]?.type !== currentValues.fields[field.name]?.type;
                      }}
                    >
                      {({ getFieldValue }) => {
                        const fieldType = getFieldValue(['fields', field.name, 'type']);
                        if (fieldType === 'select' || fieldType === 'radio' || fieldType === 'checkbox') {
                          return (
                            <Form.Item
                              {...field}
                              name={[field.name, 'options']}
                              fieldKey={[field.key, 'options']}
                              label="选项值 (用逗号分隔)"
                              rules={[{ required: true, message: '请输入选项值' }]}
                            >
                              <TextArea placeholder="选项1,选项2,选项3" />
                            </Form.Item>
                          );
                        }
                        return null;
                      }}
                    </Form.Item>
                    
                    <Form.Item
                      {...field}
                      name={[field.name, 'required']}
                      fieldKey={[field.key, 'required']}
                      label="是否必填"
                      valuePropName="checked"
                    >
                      <Select>
                        <Option value={true}>是</Option>
                        <Option value={false}>否</Option>
                      </Select>
                    </Form.Item>
                    
                    <Form.Item
                      {...field}
                      name={[field.name, 'is_key_field']}
                      fieldKey={[field.key, 'is_key_field']}
                      label="是否为关键字段"
                      valuePropName="checked"
                    >
                      <Select>
                        <Option value={true}>是</Option>
                        <Option value={false}>否</Option>
                      </Select>
                    </Form.Item>
                  </Card>
                ))}
                
                <Form.Item>
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    block
                    icon={<PlusOutlined />}
                  >
                    添加字段
                  </Button>
                  <Form.ErrorList errors={errors} />
                </Form.Item>
              </>
            )}
          </Form.List>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/dashboard/templates')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </>
  );
};

export default TemplateForm; 