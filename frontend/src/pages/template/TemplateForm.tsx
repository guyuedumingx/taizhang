import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, Typography, message, Space, Divider, Table, Modal } from 'antd';
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface TemplateField {
  id: string;
  name: string;
  type: string;
  required: boolean;
  options?: string[];
  is_key_field: boolean;
}

interface TemplateFormData {
  name: string;
  description: string;
  department: string;
  fields: TemplateField[];
}

const TemplateForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fields, setFields] = useState<TemplateField[]>([]);
  const [isFieldModalVisible, setIsFieldModalVisible] = useState(false);
  const [fieldForm] = Form.useForm();
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null);
  
  const isEdit = !!id;
  
  // 检查权限
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.TEMPLATE_EDIT : PERMISSIONS.TEMPLATE_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限执行此操作');
      navigate('/templates');
    }
  }, [hasPermission, isEdit, navigate]);

  // 如果是编辑模式，获取模板数据
  useEffect(() => {
    if (isEdit) {
      setLoading(true);
      // 模拟获取模板数据
      setTimeout(() => {
        const mockData: TemplateFormData = {
          name: `模板示例 ${id}`,
          description: '这是一个示例模板描述',
          department: '财务部',
          fields: [
            { id: '1', name: '问题类型', type: 'input', required: true, is_key_field: true },
            { id: '2', name: '严重程度', type: 'select', required: true, options: ['低', '中等', '高', '严重'], is_key_field: true },
            { id: '3', name: '责任人', type: 'input', required: true, is_key_field: true },
            { id: '4', name: '解决方案', type: 'textarea', required: false, is_key_field: false },
          ],
        };
        
        form.setFieldsValue({
          name: mockData.name,
          description: mockData.description,
          department: mockData.department,
        });
        
        setFields(mockData.fields);
        setLoading(false);
      }, 1000);
    }
  }, [form, id, isEdit]);

  // 提交表单
  const handleSubmit = async (values: any) => {
    if (fields.length === 0) {
      message.error('请至少添加一个字段');
      return;
    }
    
    setSubmitting(true);
    
    try {
      // 模拟提交数据
      const templateData = {
        ...values,
        fields,
      };
      
      console.log('提交的模板数据:', templateData);
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      message.success(isEdit ? '模板更新成功' : '模板创建成功');
      navigate('/templates');
    } catch (error) {
      message.error('操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  // 添加/编辑字段
  const showFieldModal = (index?: number) => {
    if (index !== undefined) {
      // 编辑现有字段
      const field = fields[index];
      fieldForm.setFieldsValue({
        name: field.name,
        type: field.type,
        required: field.required,
        options: field.options ? field.options.join('\n') : '',
        is_key_field: field.is_key_field,
      });
      setEditingFieldIndex(index);
    } else {
      // 添加新字段
      fieldForm.resetFields();
      setEditingFieldIndex(null);
    }
    setIsFieldModalVisible(true);
  };

  // 保存字段
  const handleSaveField = () => {
    fieldForm.validateFields().then(values => {
      const field: TemplateField = {
        id: editingFieldIndex !== null ? fields[editingFieldIndex].id : Date.now().toString(),
        name: values.name,
        type: values.type,
        required: values.required,
        options: values.type === 'select' && values.options ? values.options.split('\n').filter(Boolean) : undefined,
        is_key_field: values.is_key_field,
      };
      
      if (editingFieldIndex !== null) {
        // 更新现有字段
        const newFields = [...fields];
        newFields[editingFieldIndex] = field;
        setFields(newFields);
      } else {
        // 添加新字段
        setFields([...fields, field]);
      }
      
      setIsFieldModalVisible(false);
    });
  };

  // 删除字段
  const handleDeleteField = (index: number) => {
    const newFields = [...fields];
    newFields.splice(index, 1);
    setFields(newFields);
  };

  // 移动字段
  const handleMoveField = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) || 
      (direction === 'down' && index === fields.length - 1)
    ) {
      return;
    }
    
    const newFields = [...fields];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    [newFields[index], newFields[targetIndex]] = [newFields[targetIndex], newFields[index]];
    
    setFields(newFields);
  };

  // 字段表格列定义
  const fieldColumns: ColumnsType<TemplateField> = [
    {
      title: '字段名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          'input': '单行文本',
          'textarea': '多行文本',
          'select': '下拉选择',
          'date': '日期',
          'number': '数字',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '是否必填',
      dataIndex: 'required',
      key: 'required',
      render: (required: boolean) => required ? '是' : '否',
    },
    {
      title: '是否关键字段',
      dataIndex: 'is_key_field',
      key: 'is_key_field',
      render: (is_key_field: boolean) => is_key_field ? '是' : '否',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record, index) => (
        <Space size="small">
          <Button 
            type="text" 
            icon={<ArrowUpOutlined />} 
            onClick={() => handleMoveField(index, 'up')}
            disabled={index === 0}
          />
          <Button 
            type="text" 
            icon={<ArrowDownOutlined />} 
            onClick={() => handleMoveField(index, 'down')}
            disabled={index === fields.length - 1}
          />
          <Button 
            type="text" 
            onClick={() => showFieldModal(index)}
          >
            编辑
          </Button>
          <Button 
            type="text" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDeleteField(index)}
          />
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card loading={loading}>
        <Title level={4}>{isEdit ? '编辑模板' : '新建模板'}</Title>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入描述' }]}
          >
            <TextArea rows={4} />
          </Form.Item>
          
          <Form.Item
            label="适用部门"
            name="department"
            rules={[{ required: true, message: '请选择适用部门' }]}
          >
            <Select placeholder="选择部门">
              <Option value="财务部">财务部</Option>
              <Option value="生产部">生产部</Option>
              <Option value="客服部">客服部</Option>
              <Option value="设备部">设备部</Option>
            </Select>
          </Form.Item>
          
          <Divider orientation="left">模板字段</Divider>
          
          <div style={{ marginBottom: 16 }}>
            <Button 
              type="dashed" 
              onClick={() => showFieldModal()} 
              icon={<PlusOutlined />}
              style={{ width: '100%' }}
            >
              添加字段
            </Button>
          </div>
          
          <Table
            columns={fieldColumns}
            dataSource={fields}
            rowKey="id"
            pagination={false}
            locale={{ emptyText: '暂无字段，请添加字段' }}
          />
          
          <Form.Item style={{ marginTop: 24 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/templates')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
      
      <Modal
        title={editingFieldIndex !== null ? '编辑字段' : '添加字段'}
        open={isFieldModalVisible}
        onOk={handleSaveField}
        onCancel={() => setIsFieldModalVisible(false)}
        destroyOnClose
      >
        <Form
          form={fieldForm}
          layout="vertical"
        >
          <Form.Item
            label="字段名称"
            name="name"
            rules={[{ required: true, message: '请输入字段名称' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="字段类型"
            name="type"
            rules={[{ required: true, message: '请选择字段类型' }]}
          >
            <Select>
              <Option value="input">单行文本</Option>
              <Option value="textarea">多行文本</Option>
              <Option value="select">下拉选择</Option>
              <Option value="date">日期</Option>
              <Option value="number">数字</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="是否必填"
            name="required"
            valuePropName="checked"
            initialValue={false}
          >
            <Select>
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="是否关键字段"
            name="is_key_field"
            valuePropName="checked"
            initialValue={false}
          >
            <Select>
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.type !== currentValues.type}
          >
            {({ getFieldValue }) => 
              getFieldValue('type') === 'select' ? (
                <Form.Item
                  label="选项（每行一个选项）"
                  name="options"
                  rules={[{ required: true, message: '请输入选项' }]}
                >
                  <TextArea rows={4} placeholder="每行输入一个选项" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default TemplateForm; 