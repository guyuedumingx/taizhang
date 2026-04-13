import React, { useState, useEffect, useMemo } from 'react';
import { Table, Button, Card, Typography, Space, message, Tooltip, Empty, Alert, Select } from 'antd';
import { EyeOutlined, ReloadOutlined, FilterOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { getPendingTasks } from '../../api/approvals';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import ApprovalModal from '../../components/approval/ApprovalModal';

const { Title } = Typography;

interface Task {
  task_id: number;
  ledger_id: number;
  ledger_name: string;
  template_id: number | null;
  template_name: string | null;
  workflow_instance_id: number;
  workflow_node_id?: number;
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
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  // 从 tasks 中提取去重的模板选项
  const templateOptions = useMemo(() => {
    const map = new Map<number, string>();
    tasks.forEach(t => {
      if (t.template_id && t.template_name && !map.has(t.template_id)) {
        map.set(t.template_id, t.template_name);
      }
    });
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [tasks]);

  // 前端按模板筛选
  const filteredTasks = useMemo(() => {
    if (!selectedTemplateId) return tasks;
    return tasks.filter(t => t.template_id === selectedTemplateId);
  }, [tasks, selectedTemplateId]);
  
  // 审批相关状态
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);
  const [currentTask] = useState<Task | null>(null);

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
      const response = await getPendingTasks();
      
      // 转换响应数据以符合Task接口
      const taskList = response.map((item: Record<string, unknown>) => ({
        task_id: Number(item.task_id || 0),
        ledger_id: Number(item.ledger_id || 0),
        ledger_name: String(item.ledger_name || '未命名台账'),
        template_id: item.template_id ? Number(item.template_id) : null,
        template_name: item.template_name ? String(item.template_name) : null,
        workflow_instance_id: Number(item.workflow_instance_id || 0),
        workflow_node_id: Number(item.workflow_node_id || 0),
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


  // 处理审批成功
  const handleApprovalSuccess = () => {
    setApprovalModalVisible(false);
    fetchTasks(); // 刷新任务列表
    message.success('审批处理成功');
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
          {/* <Tooltip title="处理审批">
            <Button
              type="primary"
              size="small"
              onClick={() => openApprovalModal(record)}
            >
              处理
            </Button>
          </Tooltip> */}
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
          <Space size="middle" align="center">
            <Title level={4} style={{ margin: 0 }}>待办任务</Title>
            <Select
              placeholder="按模板筛选"
              allowClear
              style={{ width: 200 }}
              value={selectedTemplateId}
              onChange={(value) => setSelectedTemplateId(value ?? null)}
              suffixIcon={<FilterOutlined />}
              options={templateOptions.map(t => ({ label: t.name, value: t.id }))}
            />
          </Space>
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
          dataSource={filteredTasks}
          rowKey="task_id"
          loading={loading}
          pagination={{ defaultPageSize: 10 }}
          locale={{
            emptyText: <Empty description="没有待办任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          }}
        />
      </Card>

      {/* 审批对话框 */}
      {currentTask && (
        <ApprovalModal
          visible={approvalModalVisible}
          onCancel={() => setApprovalModalVisible(false)}
          onSuccess={handleApprovalSuccess}
          workflowInstanceId={currentTask.workflow_instance_id}
          ledgerId={currentTask.ledger_id}
          currentNodeId={currentTask.workflow_node_id}
        />
      )}
    </>
  );
};

export default TaskList; 