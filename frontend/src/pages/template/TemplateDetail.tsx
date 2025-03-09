import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, List, Tag, Divider, message, Spin } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { TemplateService } from '../../services/TemplateService';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { TemplateDetail as TemplateDetailType } from '../../types';

const { Title, Text } = Typography;

const TemplateDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState<boolean>(true);
  const [template, setTemplate] = useState<TemplateDetailType | null>(null);

  useEffect(() => {
    // 检查权限
    if (!hasPermission(PERMISSIONS.TEMPLATE_VIEW)) {
      message.error('您没有查看模板的权限');
      navigate('/dashboard');
      return;
    }

    if (id) {
      fetchTemplateDetails(parseInt(id, 10));
    }
  }, [id, hasPermission, navigate]);

  const fetchTemplateDetails = async (templateId: number) => {
    setLoading(true);
    try {
      const response = await TemplateService.getTemplateDetail(templateId);
      setTemplate(response);
    } catch (error) {
      console.error('获取模板详情失败:', error);
      message.error('获取模板详情失败');
      navigate('/dashboard/templates');
    } finally {
      setLoading(false);
    }
  };

  const getFieldTypeText = (type: string): string => {
    const typeMap: Record<string, string> = {
      'input': '单行文本',
      'textarea': '多行文本',
      'number': '数字',
      'select': '下拉选择',
      'radio': '单选',
      'checkbox': '多选',
      'date': '日期',
      'datetime': '日期时间'
    };
    return typeMap[type] || type;
  };

  if (loading) {
    return (
      <>
        <BreadcrumbNav 
          items={[
            { title: '模板管理', path: '/dashboard/templates' },
            { title: '加载中...' }
          ]}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        </Card>
      </>
    );
  }

  if (!template) {
    return (
      <>
        <BreadcrumbNav 
          items={[
            { title: '模板管理', path: '/dashboard/templates' },
            { title: '未找到' }
          ]}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Text type="danger">未找到模板信息</Text>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '模板管理', path: '/dashboard/templates' },
          { title: template.name }
        ]}
      />
      
      <Card>
        <Title level={4}>模板详情</Title>
        
        <Descriptions bordered column={2}>
          <Descriptions.Item label="ID">{template.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{template.name}</Descriptions.Item>
          <Descriptions.Item label="部门">{template.department}</Descriptions.Item>
          <Descriptions.Item label="描述">{template.description || '无'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{template.created_at}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{template.updated_at || '未更新'}</Descriptions.Item>
        </Descriptions>

        <Divider orientation="left">字段配置</Divider>
        
        <List
          itemLayout="horizontal"
          dataSource={template.fields || []}
          renderItem={(field, index) => (
            <List.Item>
              <Card 
                title={`${index + 1}. ${field.label} (${field.name})`} 
                style={{ width: '100%' }} 
                size="small"
              >
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="字段类型">
                    <Tag color="blue">{getFieldTypeText(field.type)}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="是否必填">
                    <Tag color={field.required ? 'red' : 'default'}>
                      {field.required ? '是' : '否'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="是否为关键字段">
                    <Tag color={field.is_key_field ? 'green' : 'default'}>
                      {field.is_key_field ? '是' : '否'}
                    </Tag>
                  </Descriptions.Item>
                  {(field.type === 'select' || field.type === 'radio' || field.type === 'checkbox') && field.options && (
                    <Descriptions.Item label="选项值" span={2}>
                      {field.options.map((option, i) => (
                        <Tag key={i} style={{ margin: '2px' }}>{option}</Tag>
                      ))}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            </List.Item>
          )}
        />
      </Card>
    </>
  );
};

export default TemplateDetail; 