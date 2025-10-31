import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, Select, message, Divider, Space, Tooltip } from 'antd';
import { MinusCircleOutlined, PlusOutlined, DragOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { TemplateService } from '../../services/TemplateService';
import { WorkflowService } from '../../services/WorkflowService';
import { TemplateCreate, TemplateUpdate, FieldCreate, Workflow, FieldUpdate } from '../../types';
import { reorderTemplateFields, FieldReorderItem } from '../../api/templates';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import useDepartments from '../../hooks/useDepartments';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// 可拖拽的字段卡片组件
interface SortableFieldCardProps {
  id: string;
  field: any;
  children: React.ReactNode;
  onRemove?: () => void;
  canRemove?: boolean;
}

const SortableFieldCard: React.FC<SortableFieldCardProps> = ({ 
  id, 
  field, 
  children, 
  onRemove,
  canRemove = true 
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.8 : 1,
    boxShadow: isDragging ? '0 4px 12px rgba(0, 0, 0, 0.15)' : 'none',
    zIndex: isDragging ? 1000 : 'auto',
    cursor: isDragging ? 'grabbing' : 'default',
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Card
        size="small"
        title={<span>字段 {field.name + 1}</span>}
        style={{ 
          marginBottom: 16,
          border: isDragging ? '2px dashed #1890ff' : '1px solid #f0f0f0',
          transition: 'all 0.2s ease',
        }}
        extra={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              {...attributes}
              {...listeners}
              style={{
                cursor: 'grab',
                padding: '6px 12px',
                borderRadius: '6px',
                backgroundColor: '#fafafa',
                border: '1px solid #d9d9d9',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                color: '#666',
                userSelect: 'none',
                transition: 'all 0.2s ease',
                minWidth: '80px',
                justifyContent: 'center',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#e6f7ff';
                e.currentTarget.style.borderColor = '#1890ff';
                e.currentTarget.style.color = '#1890ff';
                e.currentTarget.style.cursor = 'grabbing';
                e.currentTarget.style.transform = 'scale(1.02)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#fafafa';
                e.currentTarget.style.borderColor = '#d9d9d9';
                e.currentTarget.style.color = '#666';
                e.currentTarget.style.cursor = 'grab';
                e.currentTarget.style.transform = 'scale(1)';
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.cursor = 'grabbing';
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.cursor = 'grab';
              }}
            >
              <DragOutlined style={{ fontSize: '14px' }} />
              <span>拖拽排序</span>
            </div>
            {canRemove && onRemove && (
              <MinusCircleOutlined
                onClick={onRemove}
                style={{ 
                  cursor: 'pointer', 
                  color: '#ff4d4f',
                  fontSize: '16px',
                  padding: '4px',
                  borderRadius: '4px',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#fff2f0';
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              />
            )}
          </div>
        }
      >
        {children}
      </Card>
    </div>
  );
};

const TemplateForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const { options: departmentOptions } = useDepartments();
  const [fieldIds, setFieldIds] = useState<string[]>([]);
  const [savingOrder, setSavingOrder] = useState(false);
  
  const isEdit = !!id;

  // 拖拽传感器配置
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // 监听表单字段变化，同步字段ID列表
  const fieldsValue = Form.useWatch('fields', form);
  useEffect(() => {
    if (fieldsValue && Array.isArray(fieldsValue)) {
      const currentIds = fieldsValue.map((_, index) => `field-${index}`);
      const currentIdsStr = JSON.stringify(currentIds);
      const fieldIdsStr = JSON.stringify(fieldIds);
      if (currentIdsStr !== fieldIdsStr) {
        setFieldIds(currentIds);
        console.log('[字段列表] 字段数量变化，更新ID列表:', currentIds);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fieldsValue?.length]);

  // 检查权限并加载数据
  useEffect(() => {
    const requiredPermission = isEdit ? PERMISSIONS.TEMPLATE_EDIT : PERMISSIONS.TEMPLATE_CREATE;
    if (!hasPermission(requiredPermission)) {
      message.error('您没有权限执行此操作');
      navigate('/dashboard/templates');
      return;
    }

    
    // 获取工作流列表
    fetchWorkflows();

    if (isEdit) {
      fetchTemplate(parseInt(id));
    }
  }, [isEdit, id, hasPermission, navigate]);

  
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
      console.log('[模板加载] 开始加载模板详情, ID:', templateId);
      const template = await TemplateService.getTemplateDetail(templateId);
      console.log('[模板加载] 模板数据:', template);
      console.log('[模板加载] 字段数据 (原始顺序):', template.fields);
      
      // 转换字段数据格式以适应表单
      const fieldsData = template.fields.map((field, index) => ({
        name: field.name,
        label: field.label || field.name,
        type: field.type,
        required: field.required,
        options: field.options ? field.options.join(',') : '',
        is_key_field: field.is_key_field || false,  
        id: field.id,
        order: field.order || index + 1
      }));
      
      console.log('[模板加载] 转换后的字段数据:', fieldsData);
      
      // 设置表单初始值
      form.setFieldsValue({
        name: template.name,
        department: template.department,
        description: template.description || '',
        workflow_id: template.workflow_id || null,
        default_description: template.default_description || '',
        fields: fieldsData
      });
      
      // 初始化字段ID列表（用于拖拽排序）
      const ids = fieldsData.map((_, index) => `field-${index}`);
      setFieldIds(ids);
      console.log('[模板加载] 初始化字段ID列表:', ids);
      console.log('[模板加载] 字段当前order值:', fieldsData.map(f => ({ id: f.id, name: f.name, order: f.order })));
    } catch (error) {
      console.error('[模板加载] 获取模板详情失败:', error);
      message.error('获取模板详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理字段拖拽排序
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = fieldIds.indexOf(active.id as string);
      const newIndex = fieldIds.indexOf(over.id as string);
      const newFieldIds = arrayMove(fieldIds, oldIndex, newIndex);
      setFieldIds(newFieldIds);

      // 获取当前字段值并重新排序
      const currentFields = form.getFieldValue('fields') || [];
      const reorderedFields = arrayMove(currentFields, oldIndex, newIndex);
      
      // 更新表单字段值
      form.setFieldsValue({ fields: reorderedFields });

      console.log('[拖拽排序] 字段顺序已更改');
      console.log('[拖拽排序] 原顺序:', fieldIds);
      console.log('[拖拽排序] 新顺序:', newFieldIds);
      console.log('[拖拽排序] 字段索引变化:', `${oldIndex} -> ${newIndex}`);
      
      // 在编辑模式下提示用户保存顺序
      if (isEdit && id) {
        console.log('[拖拽排序] 编辑模式: 字段顺序已更新，请点击"保存字段顺序"按钮保存');
      }
    }
  };

  // 保存字段顺序（仅编辑模式）
  const handleSaveFieldOrder = async () => {
    if (!isEdit || !id) {
      console.warn('[保存顺序] 只能在编辑模式下保存顺序');
      return;
    }

    const templateId = parseInt(id);
    const fields = form.getFieldValue('fields') || [];
    
    console.log('[保存顺序] 开始保存字段顺序');
    console.log('[保存顺序] 模板ID:', templateId);
    console.log('[保存顺序] 当前字段列表:', fields);

    // 检查字段是否有ID（编辑模式下的字段应该有ID）
    const fieldsWithId = fields.filter((f: any) => f.id);
    if (fieldsWithId.length !== fields.length) {
      console.error('[保存顺序] 错误: 部分字段缺少ID');
      message.error('无法保存顺序: 部分字段缺少ID，请先保存模板');
      return;
    }

    // 构建重排序请求
    const fieldOrders: FieldReorderItem[] = fields.map((field: any, index: number) => ({
      field_id: field.id,
      order: index + 1
    }));

    console.log('[保存顺序] 准备发送的重排序请求:', fieldOrders);

    setSavingOrder(true);
    try {
      const updatedFields = await reorderTemplateFields(templateId, fieldOrders);
      
      console.log('[保存顺序] 保存成功，返回的字段:', updatedFields);
      console.log('[保存顺序] 最终字段顺序:', updatedFields.map(f => ({ id: f.id, name: f.name, order: f.order })));
      
      message.success('字段顺序保存成功');
      
      // 更新表单中的字段order值
      const updatedFieldsData = fields.map((field: any, index: number) => ({
        ...field,
        order: index + 1
      }));
      form.setFieldsValue({ fields: updatedFieldsData });
      
    } catch (error: any) {
      console.error('[保存顺序] 保存失败:', error);
      message.error(error?.response?.data?.detail || '保存字段顺序失败');
    } finally {
      setSavingOrder(false);
    }
  };

  // 提交表单
  const handleSubmit = async (values: Record<string, unknown>) => {
    console.log('[表单提交] 开始提交表单');
    console.log('[表单提交] 表单值:', values);
    
    // 转换字段数据，保持当前顺序
    const currentFields = form.getFieldValue('fields') || [];
    console.log('[表单提交] 当前字段顺序:', currentFields.map((f: any, i: number) => ({ 
      index: i, 
      id: f.id, 
      name: f.name, 
      order: f.order || i + 1 
    })));

    const fields = currentFields.map((field: any, index: number) => {
      let fieldData: FieldUpdate | FieldCreate | null = null;
      if (isEdit) {
        fieldData = {
          id: field.id as number,
          name: field.name as string,
          label: field.label as string,
          type: field.type as string,
          required: field.required as boolean || false,
          is_key_field: field.is_key_field as boolean || false,
          order: index + 1  // 按当前顺序设置order
        };
      } else {
        fieldData = {
          name: field.name as string,
          label: field.label as string,
          type: field.type as string,
          required: field.required as boolean || false,
          is_key_field: field.is_key_field as boolean || false,
          order: index + 1  // 按当前顺序设置order
        };
      }
      
      // 处理选项类型的字段
      if (field.type === 'select' || field.type === 'radio' || field.type === 'checkbox') {
        fieldData.options = field.options ? (field.options as string).split(',').map((opt: string) => opt.trim()) : [];
      }
      console.log('[表单提交] 字段数据:', fieldData);
      return fieldData;
    });
    
    console.log('[表单提交] 处理后的字段列表:', fields);
    
    setSubmitting(true);
    
    try {
      if (isEdit) {
        // 更新模板
        const updateData: TemplateUpdate = {
          name: values.name as string,
          department: values.department as string,
          description: values.description as string,
          workflow_id: values.workflow_id as number,
          default_description: values.default_description as string,
          fields: fields.filter((f: any) => f !== null && f.name !== undefined) as FieldCreate[]
        };
        
        console.log('[表单提交] 更新数据:', updateData);
        await TemplateService.updateTemplate(parseInt(id), updateData);
        console.log('[表单提交] 模板更新成功');
        message.success('模板更新成功');
      } else {
        // 创建模板
        const createData: TemplateCreate = {
          name: values.name as string,
          department: values.department as string,
          description: values.description as string,
          workflow_id: values.workflow_id as number,
          default_description: values.default_description as string,
          is_system: false,
          fields: fields.filter((f: any) => f !== null && f.name !== undefined) as FieldCreate[]
        };
        
        console.log('[表单提交] 创建数据:', createData);
        const createdTemplate = await TemplateService.createTemplate(createData);
        console.log('[表单提交] 模板创建成功:', createdTemplate);
        message.success('模板创建成功');
      }
      
      // 返回模板列表页面
      navigate('/dashboard/templates');
    } catch (error) {
      console.error('[表单提交] 模板操作失败:', error);
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
              {departmentOptions.map((option) => (
                <Option key={option.value} value={option.value}>{option.label}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="description"
            label="模板描述"
          >
            <TextArea rows={4} placeholder="请输入模板描述" />
          </Form.Item>
          
          <Form.Item
            name="workflow_id"
            label="关联工作流"
          >
            <Select placeholder="选择关联工作流" allowClear>
              {workflows.map(workflow => (
                <Option key={workflow.id} value={workflow.id}>{workflow.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Divider orientation="left">
            字段配置
            {isEdit && fieldIds.length > 0 && (
              <Tooltip title="拖拽字段卡片左侧的'拖拽排序'按钮可以调整字段顺序，调整后请点击保存按钮">
                <Button 
                  type="link" 
                  size="small" 
                  onClick={handleSaveFieldOrder}
                  loading={savingOrder}
                  style={{ marginLeft: 16 }}
                >
                  保存字段顺序
                </Button>
              </Tooltip>
            )}
            {fieldIds.length > 1 && (
              <span style={{ 
                marginLeft: 16, 
                fontSize: '12px', 
                color: '#666',
                fontStyle: 'italic'
              }}>
                💡 提示：拖拽'拖拽排序'按钮可调整字段顺序
              </span>
            )}
          </Divider>
          
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
            {(fields, { add, remove }, { errors }) => {
              return (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={fieldIds}
                    strategy={verticalListSortingStrategy}
                  >
                    <>
                      {fields.map((field, index) => (
                        <SortableFieldCard
                          key={field.key}
                          id={fieldIds[index] || `field-${index}`}
                          field={field}
                          canRemove={fields.length > 1}
                          onRemove={() => {
                            console.log('[字段删除] 删除字段，索引:', field.name);
                            remove(field.name);
                          }}
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
                        </SortableFieldCard>
                      ))}
                      
                      <Form.Item>
                        <Button
                          type="dashed"
                          onClick={() => {
                            console.log('[字段添加] 添加新字段');
                            add();
                          }}
                          block
                          icon={<PlusOutlined />}
                        >
                          添加字段
                        </Button>
                        <Form.ErrorList errors={errors} />
                      </Form.Item>
                    </>
                  </SortableContext>
                </DndContext>
              );
            }}
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