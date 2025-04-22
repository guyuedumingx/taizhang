import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Popconfirm, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FieldBinaryOutlined, FileTextOutlined, BranchesOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { TemplateService } from '../../services/TemplateService';
import { Template } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Search } = Input;

const TemplateList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [searchText, setSearchText] = useState('');

  // 获取模板列表
  const fetchTemplates = async () => {
    if (!hasPermission(PERMISSIONS.TEMPLATE_VIEW)) {
      message.error('您没有查看模板的权限');
      navigate('/dashboard');
      return;
    }
    
    setLoading(true);
    try {
      const data = await TemplateService.getTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('获取模板列表失败:', error);
      message.error('获取模板列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleDelete = async (id: number) => {
    try {
      await TemplateService.deleteTemplate(id);
      message.success('删除模板成功');
      fetchTemplates();
    } catch (error) {
      console.error('删除模板失败:', error);
      message.error('删除模板失败');
    }
  };

  const filteredTemplates = templates.filter(template =>
    template.name.toLowerCase().includes(searchText.toLowerCase()) ||
    template.description?.toLowerCase().includes(searchText.toLowerCase()) ||
    template.department.toLowerCase().includes(searchText.toLowerCase()) ||
    template.created_by_name?.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns: ColumnsType<Template> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      filters: [
        { text: '财务部', value: '财务部' },
        { text: '生产部', value: '生产部' },
        { text: '客服部', value: '客服部' },
        { text: '设备部', value: '设备部' },
      ],
      onFilter: (value, record) => record.department === value.toString(),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '字段数量',
      dataIndex: 'fields_count',
      key: 'fields_count',
      sorter: (a, b) => a.fields_count - b.fields_count,
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a, b) => a.created_at.localeCompare(b.created_at),
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 250,
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<FieldBinaryOutlined />}
            onClick={() => navigate(`/dashboard/templates/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_VIEW)}
            title="查看字段"
          />
          <Button
            type="text"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/dashboard/templates/${record.id}/ledgers`)}
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_VIEW) || !hasPermission(PERMISSIONS.LEDGER_VIEW)}
            title="查看台账汇总"
          />
          <Button
            type="text"
            icon={<BranchesOutlined />}
            onClick={() => navigate(`/dashboard/workflow/${record.workflow_id}`)}
            disabled={!hasPermission(PERMISSIONS.WORKFLOW_VIEW)}
            title="关联工作流"
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/dashboard/templates/edit/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_EDIT)}
            title="编辑模板"
          />
          <Popconfirm
            title="确定要删除这个模板吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_DELETE) || record.is_system}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.TEMPLATE_DELETE) || record.is_system}
              title={record.is_system ? '系统模板不能删除' : '删除模板'}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '模板管理', path: '/dashboard/templates' }
        ]}
        showBackButton={false}
      />
      
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>模板管理</Title>
          <Space>
            <Search
              placeholder="搜索模板"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/dashboard/templates/new')}
              disabled={!hasPermission(PERMISSIONS.TEMPLATE_CREATE)}
            >
              添加模板
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredTemplates}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>
    </>
  );
};

export default TemplateList; 