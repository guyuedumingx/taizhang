import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, Typography, DatePicker, message, Space, Divider } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import dayjs from 'dayjs';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface LedgerFormData {
  title: string;
  department: string;
  teamId: number;
  description: string;
  date: string;
  status: string;
  fields: Array<{
    id: string;
    name: string;
    value: string;
  }>;
}

const LedgerForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [templates, setTemplates] = useState<Array<{ id: number; name: string }>>([]);
  const [teams, setTeams] = useState<Array<{ id: number; name: string }>>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [templateFields, setTemplateFields] = useState<Array<{ id: string; name: string; type: string }>>([]);
  
  const isEdit = !!id;
  
  // 检查权限
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.LEDGER_EDIT : PERMISSIONS.LEDGER_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限执行此操作');
      navigate('/ledgers');
    }
  }, [hasPermission, isEdit, navigate]);

  // 获取模板列表
  useEffect(() => {
    // 模拟获取模板列表
    setTimeout(() => {
      setTemplates([
        { id: 1, name: '财务差错模板' },
        { id: 2, name: '生产质量问题模板' },
        { id: 3, name: '客户投诉模板' },
        { id: 4, name: '设备故障模板' },
      ]);
      
      setTeams([
        { id: 1, name: '财务团队' },
        { id: 2, name: '生产团队' },
        { id: 3, name: '客服团队' },
        { id: 4, name: '设备团队' },
      ]);
    }, 500);
  }, []);

  // 如果是编辑模式，获取台账数据
  useEffect(() => {
    if (isEdit) {
      setLoading(true);
      // 模拟获取台账数据
      setTimeout(() => {
        const mockData: LedgerFormData = {
          title: `台账示例 ${id}`,
          department: '财务部',
          teamId: 1,
          description: '这是一个示例台账描述',
          date: '2023-05-15',
          status: '处理中',
          fields: [
            { id: 'field1', name: '问题类型', value: '数据错误' },
            { id: 'field2', name: '严重程度', value: '中等' },
            { id: 'field3', name: '责任人', value: '张三' },
            { id: 'field4', name: '解决方案', value: '重新核对数据并更正' },
          ],
        };
        
        form.setFieldsValue({
          ...mockData,
          date: dayjs(mockData.date),
          templateId: 1, // 假设使用了模板1
        });
        
        setSelectedTemplate(1);
        setTemplateFields([
          { id: 'field1', name: '问题类型', type: 'input' },
          { id: 'field2', name: '严重程度', type: 'select' },
          { id: 'field3', name: '责任人', type: 'input' },
          { id: 'field4', name: '解决方案', type: 'textarea' },
        ]);
        
        setLoading(false);
      }, 1000);
    }
  }, [form, id, isEdit]);

  // 处理模板选择
  const handleTemplateChange = (templateId: number) => {
    setSelectedTemplate(templateId);
    
    // 模拟获取模板字段
    setTimeout(() => {
      const fields = [
        { id: 'field1', name: '问题类型', type: 'input' },
        { id: 'field2', name: '严重程度', type: 'select' },
        { id: 'field3', name: '责任人', type: 'input' },
        { id: 'field4', name: '解决方案', type: 'textarea' },
      ];
      
      setTemplateFields(fields);
      
      // 清除之前的字段值
      const currentValues = form.getFieldsValue();
      const newValues = { ...currentValues };
      newValues.fields = {};
      form.setFieldsValue(newValues);
    }, 500);
  };

  // 提交表单
  const handleSubmit = async (values: any) => {
    if (!selectedTemplate) {
      message.error('请选择模板');
      return;
    }
    
    setSubmitting(true);
    
    try {
      // 模拟提交数据
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      message.success(isEdit ? '台账更新成功' : '台账创建成功');
      navigate('/ledgers');
    } catch (error) {
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
          const fieldName = `fields[${field.id}]`;
          
          if (field.type === 'input') {
            return (
              <Form.Item
                key={field.id}
                label={field.name}
                name={fieldName}
                rules={[{ required: true, message: `请输入${field.name}` }]}
              >
                <Input />
              </Form.Item>
            );
          }
          
          if (field.type === 'textarea') {
            return (
              <Form.Item
                key={field.id}
                label={field.name}
                name={fieldName}
                rules={[{ required: true, message: `请输入${field.name}` }]}
              >
                <TextArea rows={4} />
              </Form.Item>
            );
          }
          
          if (field.type === 'select') {
            return (
              <Form.Item
                key={field.id}
                label={field.name}
                name={fieldName}
                rules={[{ required: true, message: `请选择${field.name}` }]}
              >
                <Select>
                  <Option value="低">低</Option>
                  <Option value="中等">中等</Option>
                  <Option value="高">高</Option>
                  <Option value="严重">严重</Option>
                </Select>
              </Form.Item>
            );
          }
          
          return null;
        })}
      </>
    );
  };

  return (
    <Card loading={loading}>
      <Title level={4}>{isEdit ? '编辑台账' : '新建台账'}</Title>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          status: '处理中',
          date: dayjs(),
        }}
      >
        <Form.Item
          label="模板"
          name="templateId"
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
          label="台账标题"
          name="title"
          rules={[{ required: true, message: '请输入台账标题' }]}
        >
          <Input />
        </Form.Item>
        
        <Form.Item
          label="部门"
          name="department"
          rules={[{ required: true, message: '请选择部门' }]}
        >
          <Select placeholder="选择部门">
            <Option value="财务部">财务部</Option>
            <Option value="生产部">生产部</Option>
            <Option value="客服部">客服部</Option>
            <Option value="设备部">设备部</Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          label="团队"
          name="teamId"
          rules={[{ required: true, message: '请选择团队' }]}
        >
          <Select placeholder="选择团队">
            {teams.map(team => (
              <Option key={team.id} value={team.id}>{team.name}</Option>
            ))}
          </Select>
        </Form.Item>
        
        <Form.Item
          label="日期"
          name="date"
          rules={[{ required: true, message: '请选择日期' }]}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        
        <Form.Item
          label="状态"
          name="status"
          rules={[{ required: true, message: '请选择状态' }]}
        >
          <Select>
            <Option value="处理中">处理中</Option>
            <Option value="已完成">已完成</Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          label="描述"
          name="description"
          rules={[{ required: true, message: '请输入描述' }]}
        >
          <TextArea rows={4} />
        </Form.Item>
        
        {renderTemplateFields()}
        
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={submitting}>
              {isEdit ? '更新' : '创建'}
            </Button>
            <Button onClick={() => navigate('/ledgers')}>取消</Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default LedgerForm; 