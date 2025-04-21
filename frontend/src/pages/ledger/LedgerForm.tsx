import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, Typography, DatePicker, message, Space, Divider } from 'antd';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { TemplateService } from '../../services/TemplateService';
import { TeamService } from '../../services/TeamService';
import { Template, Team, Field } from '../../types';
import dayjs from 'dayjs';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface FormValues {
  name: string;
  team_id: number;
  description?: string;
  date: dayjs.Dayjs;
  status: string;
  template_id: number;
  data: Record<string, string>;
}

const LedgerForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [templateFields, setTemplateFields] = useState<Field[]>([]);
  
  const isEdit = !!id;
  
  // 从URL参数获取template_id和name
  const getUrlParams = () => {
    const queryParams = new URLSearchParams(location.search);
    const templateId = queryParams.get('template_id');
    const name = queryParams.get('name');
    return { templateId, name };
  };
  
  // 检查权限
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.LEDGER_EDIT : PERMISSIONS.LEDGER_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限执行此操作');
      navigate('/dashboard/ledgers');
      return;
    }
    
    // 获取模板和团队列表
    fetchTemplatesAndTeams();
    
    // 如果是编辑模式，获取台账数据
    if (isEdit) {
      fetchLedger(parseInt(id));
    } else {
      // 如果是新建模式，检查URL参数
      const { templateId, name } = getUrlParams();
      if (templateId) {
        const parsedTemplateId = parseInt(templateId);
        setSelectedTemplate(parsedTemplateId);
        fetchTemplateFields(parsedTemplateId);
        
        // 设置初始表单值
        form.setFieldsValue({
          template_id: parsedTemplateId,
          name: name ? decodeURIComponent(name) : '',
        });
      }
    }
  }, [hasPermission, isEdit, id, navigate, form, location.search]);

  // 获取模板和团队数据
  const fetchTemplatesAndTeams = async () => {
    setLoading(true);
    try {
      const [templatesData, teamsData] = await Promise.all([
        TemplateService.getTemplates(),
        TeamService.getTeams()
      ]);
      
      setTemplates(templatesData);
      setTeams(teamsData);
    } catch (error) {
      console.error('获取数据失败:', error);
      message.error('获取模板和团队数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取台账详情
  const fetchLedger = async (ledgerId: number) => {
    setLoading(true);
    try {
      const ledger = await LedgerService.getLedger(ledgerId);
      
      // 设置表单初始值
      form.setFieldsValue({
        name: ledger.name,
        description: ledger.description,
        team_id: ledger.team_id,
        template_id: ledger.template_id,
        status: ledger.status,
        data: ledger.data || {},
      });
      
      // 如果有模板ID，获取模板字段
      if (ledger.template_id) {
        setSelectedTemplate(ledger.template_id);
        await fetchTemplateFields(ledger.template_id);
      }
    } catch (error) {
      console.error('获取台账详情失败:', error);
      message.error('获取台账详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取模板字段
  const fetchTemplateFields = async (templateId: number) => {
    setLoading(true);
    try {
      const template = await TemplateService.getTemplateDetail(templateId);
      if (template) {
        setTemplateFields(template.fields || []);
        
        // 使用模板默认值填充表单
        const formValues: Record<string, unknown> = {
          template_id: templateId,
        };
        
        if (template.default_description && !form.getFieldValue('description')) {
          formValues.description = template.default_description;
        }
        
        // 更新表单值
        form.setFieldsValue(formValues);
      }
    } catch (error) {
      console.error('获取模板字段失败:', error);
      message.error('获取模板字段失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理模板变更
  const handleTemplateChange = (value: number) => {
    setSelectedTemplate(value);
    fetchTemplateFields(value);
  };

  // 提交表单
  const handleSubmit = async (values: FormValues) => {
    if (!selectedTemplate) {
      message.error('请选择模板');
      return;
    }
    
    setSubmitting(true);
    
    try {
      // 获取当前选中的模板详情
      const template = await TemplateService.getTemplateDetail(selectedTemplate);
      
      // 准备提交数据，使用合适的类型
      const submitData = {
        template_id: values.template_id,
        data: values.data || {},
        name: values.name || '',
        description: values.description || template.default_description || '',
        status: values.status || 'draft',
        team_id: values.team_id || null
      };
      
      if (isEdit) {
        // 更新台账
        await LedgerService.updateLedger(parseInt(id), submitData);
        message.success('台账更新成功');
      } else {
        // 创建台账
        await LedgerService.createLedger(submitData);
        message.success('台账创建成功');
      }
      
      // 返回台账列表页面
      navigate('/dashboard/ledgers');
    } catch (error) {
      console.error('台账操作失败:', error);
      message.error('操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  // 渲染模板字段
  const renderTemplateFields = () => {
    if (!selectedTemplate || templateFields.length === 0) {
      return null;
    }
    
    return (
      <>
        <Divider orientation="left">模板字段</Divider>
        {templateFields.map(field => {
          const fieldName = ['data', field.name];
          
          // 根据字段类型渲染不同的表单控件
          if (field.type === 'input') {
            return (
              <Form.Item
                key={field.id}
                label={field.label || field.name}
                name={fieldName}
                rules={[{ required: field.required, message: `请输入${field.label || field.name}` }]}
              >
                <Input />
              </Form.Item>
            );
          }
          
          if (field.type === 'textarea') {
            return (
              <Form.Item
                key={field.id}
                label={field.label || field.name}
                name={fieldName}
                rules={[{ required: field.required, message: `请输入${field.label || field.name}` }]}
              >
                <TextArea rows={4} />
              </Form.Item>
            );
          }
          
          if (field.type === 'select' && field.options) {
            return (
              <Form.Item
                key={field.id}
                label={field.label || field.name}
                name={fieldName}
                rules={[{ required: field.required, message: `请选择${field.label || field.name}` }]}
              >
                <Select>
                  {field.options.map(option => (
                    <Option key={option} value={option}>{option}</Option>
                  ))}
                </Select>
              </Form.Item>
            );
          }
          
          if (field.type === 'number') {
            return (
              <Form.Item
                key={field.id}
                label={field.label || field.name}
                name={fieldName}
                rules={[{ required: field.required, message: `请输入${field.label || field.name}` }]}
              >
                <Input type="number" />
              </Form.Item>
            );
          }
          
          if (field.type === 'date') {
            return (
              <Form.Item
                key={field.id}
                label={field.label || field.name}
                name={fieldName}
                rules={[{ required: field.required, message: `请选择${field.label || field.name}` }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            );
          }
          
          // 默认使用文本输入框
          return (
            <Form.Item
              key={field.id}
              label={field.label || field.name}
              name={fieldName}
              rules={[{ required: field.required, message: `请输入${field.label || field.name}` }]}
            >
              <Input />
            </Form.Item>
          );
        })}
      </>
    );
  };

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '台账管理', path: '/dashboard/ledgers' },
          { title: isEdit ? '编辑台账' : '创建台账' }
        ]}
        backButtonText="返回列表"
        onBack={() => navigate('/dashboard/ledgers')}
      />
      
      <Card loading={loading}>
        <Title level={4}>{isEdit ? '编辑台账' : '创建台账'}</Title>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            status: 'draft',
            data: {}
          }}
        >
          <Form.Item
            label="模板"
            name="template_id"
            rules={[{ required: true, message: '请选择模板' }]}
          >
            <Select
              placeholder="选择模板"
              onChange={handleTemplateChange}
              disabled={isEdit}
            >
              {templates.map(template => (
                <Option key={template.id} value={template.id}>{template.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          {(
            <>
              <Form.Item
                label="台账名称"
                name="name"
                rules={[{ required: true, message: '请输入台账名称' }]}
              >
                <Input />
              </Form.Item>
              
              <Form.Item
                label="所属团队"
                name="team_id"
                rules={[{ required: true, message: '请选择所属团队' }]}
              >
                <Select placeholder="选择团队">
                  {teams.map(team => (
                    <Option key={team.id} value={team.id}>{team.name}</Option>
                  ))}
                </Select>
              </Form.Item>
              
              <Form.Item
                label="台账描述"
                name="description"
              >
                <TextArea rows={4} />
              </Form.Item>
              
              <Form.Item
                label="状态"
                name="status"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select>
                  <Option value="draft">草稿</Option>
                </Select>
              </Form.Item>
            </>
          )}
          
          {/* 仅在选择模板后显示模板字段 */}
          {selectedTemplate && renderTemplateFields()}
          
          <Divider />
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {isEdit ? '更新台账' : '创建台账'}
              </Button>
              <Button onClick={() => navigate('/dashboard/ledgers')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </>
  );
};

export default LedgerForm; 