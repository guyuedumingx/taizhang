import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, Typography, DatePicker, message, Space, Divider } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { TemplateService } from '../../services/TemplateService';
import { TeamService } from '../../services/TeamService';
import { Ledger, LedgerCreate, LedgerUpdate, Template, Team, Field } from '../../types';
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
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [templateFields, setTemplateFields] = useState<Field[]>([]);
  
  const isEdit = !!id;
  
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
    }
  }, [hasPermission, isEdit, id, navigate]);

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

  // 处理模板选择
  const handleTemplateChange = async (templateId: number) => {
    setSelectedTemplate(templateId);
    await fetchTemplateFields(templateId);
  };

  // 获取模板字段
  const fetchTemplateFields = async (templateId: number) => {
    try {
      const templateDetail = await TemplateService.getTemplate(templateId);
      
      if (templateDetail.fields) {
        setTemplateFields(templateDetail.fields);
        
        // 重置表单中的数据字段
        const currentValues = form.getFieldsValue();
        form.setFieldsValue({
          ...currentValues,
          data: {}
        });
      }
    } catch (error) {
      console.error('获取模板字段失败:', error);
      message.error('获取模板字段失败');
    }
  };

  // 提交表单
  const handleSubmit = async (values: FormValues) => {
    if (!selectedTemplate) {
      message.error('请选择模板');
      return;
    }
    
    setSubmitting(true);
    
    try {
      // 准备提交数据
      const submitData = {
        name: values.name,
        description: values.description,
        team_id: values.team_id,
        template_id: values.template_id,
        status: values.status,
        data: values.data
      };
      
      if (isEdit) {
        // 更新台账
        await LedgerService.updateLedger(parseInt(id), submitData as LedgerUpdate);
        message.success('台账更新成功');
      } else {
        // 创建台账
        await LedgerService.createLedger(submitData as LedgerCreate);
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
              <Option value="active">处理中</Option>
              <Option value="completed">已完成</Option>
            </Select>
          </Form.Item>
          
          {renderTemplateFields()}
          
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