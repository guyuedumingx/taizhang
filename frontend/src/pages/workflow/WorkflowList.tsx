import React, { useState, useEffect } from 'react';
import { Table, Button, Card, Typography, Tag, Space, message, Tooltip, Popconfirm, Input } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ExclamationCircleOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { WorkflowService } from '../../services/WorkflowService';
import type { ColumnsType } from 'antd/es/table';
import { Workflow } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Search } = Input;

const WorkflowList: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [searchText, setSearchText] = useState<string>('');
  const navigate = useNavigate();
  const location = useLocation();
  const { hasPermission } = useAuthStore();
  
  // 从URL查询参数中获取模板ID
  const queryParams = new URLSearchParams(location.search);
  const templateId = queryParams.get('template_id');

  useEffect(() => {
    // 检查权限
    if (!hasPermission(PERMISSIONS.WORKFLOW_VIEW)) {
      message.error('您没有查看工作流程的权限');
      navigate('/dashboard');
      return;
    }

    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response = await WorkflowService.getWorkflows();
      setWorkflows(response);
      
    } catch (error) {
      console.error('获取工作流程失败:', error);
      message.error('获取工作流程失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await WorkflowService.deleteWorkflow(id);
      message.success('删除工作流程成功');
      fetchWorkflows();
    } catch (error) {
      console.error('删除工作流程失败:', error);
      message.error('删除工作流程失败');
    }
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  // 过滤工作流数据
  const filteredWorkflows = workflows.filter(workflow => {
    // 处理搜索过滤
    if (searchText) {
      return (
        workflow.name.toLowerCase().includes(searchText.toLowerCase()) ||
        (workflow.description && workflow.description.toLowerCase().includes(searchText.toLowerCase())) ||
        (workflow.template_name && workflow.template_name.toLowerCase().includes(searchText.toLowerCase()))
      );
    }
    
    return true;
  });

  const columns: ColumnsType<Workflow> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="middle">
          {hasPermission(PERMISSIONS.WORKFLOW_EDIT) && (
            <Tooltip title="编辑">
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => {
                  console.log(`导航到工作流编辑页面，ID: ${record.id}`);
                  navigate(`/dashboard/workflow/edit/${record.id}`);
                }}
              />
            </Tooltip>
          )}
          {hasPermission(PERMISSIONS.WORKFLOW_DELETE) && (
            <Tooltip title="删除">
              <Popconfirm
                title="确定要删除这个工作流程吗？"
                icon={<ExclamationCircleOutlined style={{ color: 'red' }} />}
                onConfirm={() => handleDelete(record.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <BreadcrumbNav 
        items={[
          ...(templateId ? [{ title: '模板管理', path: '/dashboard/templates' }] : []),
          { title: '工作流管理', path: '/dashboard/workflow' }
        ]}
        showBackButton={templateId ? true : false}
        onBack={templateId ? () => navigate(`/dashboard/templates`) : undefined}
      />
      
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>
            工作流程管理
            {templateId && <Tag color="blue" style={{ marginLeft: 8 }}>模板筛选</Tag>}
          </Title>
          <Space>
            <Search
              placeholder="搜索工作流"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            {hasPermission(PERMISSIONS.WORKFLOW_CREATE) && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate(`/dashboard/workflow/create${templateId ? `?template_id=${templateId}` : ''}`)}
              >
                新建工作流程
              </Button>
            )}
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredWorkflows}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </>
  );
};

export default WorkflowList; 