import React, { useState, useEffect } from 'react';
import { Table, Button, Card, Typography, Space, message, Tooltip } from 'antd';
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import api from '../../api';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;

interface Task {
  task_id: number;
  ledger_id: number;
  ledger_name: string;
  workflow_instance_id: number;
  workflow_node_name: string;
  created_by: string;
  created_at: string;
}

const TaskList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<Task[]>([]);

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.LEDGER_APPROVE)) {
      message.error('您没有权限访问此页面');
      navigate('/dashboard');
      return;
    }

    fetchTasks();
  }, [hasPermission, navigate]);

  // 获取待办任务
  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await api.approvals.getPendingTasks();
      // 转换响应数据以符合Task接口
      const taskList = response.map((item: Record<string, unknown>) => ({
        task_id: Number(item.id || 0),
        ledger_id: Number(item.ledger_id || 0),
        ledger_name: String(item.ledger_name || '未命名台账'),
        workflow_instance_id: Number(item.workflow_instance_id || 0),
        workflow_node_name: String(item.workflow_node_name || '未知节点'),
        created_by: String(item.created_by || '未知用户'),
        created_at: String(item.created_at || new Date().toISOString())
      }));
      setTasks(taskList);
    } catch (error) {
      console.error('获取待办任务失败:', error);
      message.error('获取待办任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理审批
  const handleApprove = async (ledgerId: number) => {
    try {
      await api.approvals.approveLedger(ledgerId, {
        action: 'approve',
        comment: '同意',
      });
      message.success('审批通过成功');
      fetchTasks();
    } catch (error) {
      console.error('审批失败:', error);
      message.error('审批失败');
    }
  };

  // 处理拒绝
  const handleReject = async (ledgerId: number) => {
    try {
      await api.approvals.approveLedger(ledgerId, {
        action: 'reject',
        comment: '不同意',
      });
      message.success('已拒绝');
      fetchTasks();
    } catch (error) {
      console.error('拒绝失败:', error);
      message.error('拒绝失败');
    }
  };

  // 表格列定义
  const columns: ColumnsType<Task> = [
    {
      title: '台账ID',
      dataIndex: 'ledger_id',
      key: 'ledger_id',
      width: 80,
    },
    {
      title: '台账名称',
      dataIndex: 'ledger_name',
      key: 'ledger_name',
      render: (text, record) => (
        <a onClick={() => navigate(`/dashboard/ledgers/${record.ledger_id}`)}>{text}</a>
      ),
    },
    {
      title: '当前节点',
      dataIndex: 'workflow_node_name',
      key: 'workflow_node_name',
    },
    {
      title: '提交人',
      dataIndex: 'created_by',
      key: 'created_by',
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/dashboard/ledgers/${record.ledger_id}`)}
            />
          </Tooltip>
          <Tooltip title="同意">
            <Button
              type="text"
              icon={<CheckOutlined style={{ color: 'green' }} />}
              onClick={() => handleApprove(record.ledger_id)}
            />
          </Tooltip>
          <Tooltip title="拒绝">
            <Button
              type="text"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleReject(record.ledger_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '审批任务', path: '/dashboard/approval/tasks' }
        ]}
        showBackButton={false}
      />
      
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>待办任务</Title>
          <Button type="primary" onClick={fetchTasks}>刷新</Button>
        </div>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="task_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </>
  );
};

export default TaskList; 