import React, { useState, useEffect } from 'react';
import { Table, Button, Card, Typography, Tag, Space, message, Tooltip, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import api from '../../api';
import type { ColumnsType } from 'antd/es/table';
import { Workflow } from '../../types';

const { Title } = Typography;

const WorkflowList: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();

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
      const response = await api.workflows.getWorkflows();
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
      await api.workflows.deleteWorkflow(id);
      message.success('删除工作流程成功');
      fetchWorkflows();
    } catch (error) {
      console.error('删除工作流程失败:', error);
      message.error('删除工作流程失败');
    }
  };

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
      title: '模板',
      dataIndex: ['template', 'name'],
      key: 'template',
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
                onClick={() => navigate(`/workflow/edit/${record.id}`)}
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
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>工作流程管理</Title>
        {hasPermission(PERMISSIONS.WORKFLOW_CREATE) && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/workflow/create')}
          >
            新建工作流程
          </Button>
        )}
      </div>
      <Table
        columns={columns}
        dataSource={workflows}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
};

export default WorkflowList; 