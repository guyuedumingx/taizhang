import React, { useState, useEffect } from 'react';
import { Table, Button, Card, Typography, Space, message, Tooltip, Empty, Alert } from 'antd';
import { CheckOutlined, CloseOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { ApprovalService } from '../../services/ApprovalService';
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
  const [error, setError] = useState<string | null>(null);

  // 检查权限
  useEffect(() => {
    console.log('TaskList组件已挂载，检查权限...');
    
    if (!hasPermission(PERMISSIONS.LEDGER_APPROVE)) {
      console.log('用户没有审批权限，重定向到首页');
      message.error('您没有权限访问此页面');
      navigate('/dashboard');
      return;
    }

    console.log('用户有审批权限，正在加载待办任务...');
    fetchTasks();
  }, [hasPermission, navigate]);

  // 获取待办任务
  const fetchTasks = async () => {
    console.log('开始加载待办任务...');
    setLoading(true);
    setError(null);
    try {
      console.log('调用ApprovalService.getPendingTasks()...');
      const response = await ApprovalService.getPendingTasks();
      
      console.log('API响应数据:', response);
      
      if (!response || !Array.isArray(response)) {
        console.error('API返回格式不正确:', response);
        setError('获取任务数据格式不正确');
        setTasks([]);
        return;
      }
      
      // 转换响应数据以符合Task接口
      const taskList = response.map((item: Record<string, unknown>) => ({
        task_id: Number(item.task_id || 0),
        ledger_id: Number(item.ledger_id || 0),
        ledger_name: String(item.ledger_name || '未命名台账'),
        workflow_instance_id: Number(item.workflow_instance_id || 0),
        workflow_node_name: String(item.workflow_node_name || '未知节点'),
        created_by: String(item.created_by || '未知用户'),
        created_at: String(item.created_at || new Date().toISOString())
      }));
      
      console.log('处理后的任务列表:', taskList);
      setTasks(taskList);
    } catch (error) {
      console.error('获取待办任务失败:', error);
      setError('获取待办任务失败，请稍后重试');
      message.error('获取待办任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理审批
  const handleApprove = async (taskId: number, instanceId: number) => {
    try {
      await ApprovalService.approveWorkflowNode(instanceId, taskId, {
        comment: '同意',
      });
      message.success('审批通过成功');
      fetchTasks();
    } catch (error) {
      console.error('审批失败:', error);
      message.error('审批失败，请稍后重试');
    }
  };

  // 处理拒绝
  const handleReject = async (taskId: number, instanceId: number) => {
    try {
      await ApprovalService.rejectWorkflowNode(instanceId, taskId, {
        comment: '不同意',
      });
      message.success('已拒绝审批');
      fetchTasks();
    } catch (error) {
      console.error('拒绝失败:', error);
      message.error('拒绝失败，请稍后重试');
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
              onClick={() => handleApprove(record.task_id, record.workflow_instance_id)}
            />
          </Tooltip>
          <Tooltip title="拒绝">
            <Button
              type="text"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleReject(record.task_id, record.workflow_instance_id)}
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
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            onClick={fetchTasks}
            loading={loading}
          >
            刷新
          </Button>
        </div>
        
        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            action={
              <Button size="small" type="primary" onClick={fetchTasks}>
                重试
              </Button>
            }
          />
        )}
        
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="task_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{
            emptyText: <Empty description="没有待办任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          }}
        />
      </Card>
    </>
  );
};

export default TaskList; 