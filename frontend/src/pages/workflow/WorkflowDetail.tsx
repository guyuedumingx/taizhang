import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Tag, Steps, Divider, message, Spin } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { WorkflowService } from '../../services/WorkflowService';
import { Workflow, WorkflowNode } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Step } = Steps;

const WorkflowDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState<boolean>(true);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();

  useEffect(() => {
    // 检查权限
    if (!hasPermission(PERMISSIONS.WORKFLOW_VIEW)) {
      message.error('您没有查看工作流程的权限');
      navigate('/dashboard');
      return;
    }

    if (id) {
      fetchWorkflowDetail(parseInt(id, 10));
    }
  }, [id]);

  const fetchWorkflowDetail = async (workflowId: number) => {
    setLoading(true);
    try {
      const response = await WorkflowService.getWorkflow(workflowId);
      setWorkflow(response);
    } catch (error) {
      console.error('获取工作流程详情失败:', error);
      message.error('获取工作流程详情失败');
      navigate('/dashboard/workflow');
    } finally {
      setLoading(false);
    }
  };

  // 获取节点类型对应的标签颜色
  const getNodeTypeColor = (nodeType: string): string => {
    switch (nodeType) {
      case 'start':
        return 'blue';
      case 'approval':
        return 'orange';
      case 'end':
        return 'green';
      default:
        return 'default';
    }
  };

  // 获取节点类型的中文名称
  const getNodeTypeName = (nodeType: string): string => {
    switch (nodeType) {
      case 'start':
        return '开始';
      case 'approval':
        return '审批';
      case 'end':
        return '结束';
      default:
        return nodeType;
    }
  };

  // 获取审批人信息
  const getApproverInfo = (node: WorkflowNode): string => {
    if (node.node_type !== 'approval') {
      return '无需审批';
    }

    if (node.approver_role_id) {
      return `角色ID: ${node.approver_role_id}`;
    }
    
    return '';
  };

  if (loading) {
    return (
      <>
        <BreadcrumbNav 
          items={[
            { title: '工作流管理', path: '/dashboard/workflow' },
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

  if (!workflow) {
    return (
      <>
        <BreadcrumbNav 
          items={[
            { title: '工作流管理', path: '/dashboard/workflow' },
            { title: '未找到' }
          ]}
        />
        <Card>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Typography.Text type="danger">未找到工作流程信息</Typography.Text>
          </div>
        </Card>
      </>
    );
  }

  // 按照顺序排序节点
  const sortedNodes = [...workflow.nodes].sort((a, b) => a.order_index - b.order_index);

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '工作流管理', path: '/dashboard/workflow' },
          { title: workflow.name }
        ]}
        backButtonText="返回列表"
        onBack={() => navigate('/dashboard/workflow')}
      />
      
      <Card>
        <Title level={4}>工作流程详情</Title>
        
        <Descriptions bordered column={2}>
          <Descriptions.Item label="ID">{workflow.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{workflow.name}</Descriptions.Item>
          <Descriptions.Item label="描述">{workflow.description || '无'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={workflow.is_active ? 'green' : 'red'}>
              {workflow.is_active ? '启用' : '禁用'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{workflow.created_at}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{workflow.updated_at || '未更新'}</Descriptions.Item>
        </Descriptions>

        <Divider orientation="left">工作流程节点</Divider>
        
        <Steps direction="vertical" current={-1}>
          {sortedNodes.map((node) => (
            <Step
              key={node.id}
              title={node.name}
              description={
                <div>
                  <p>{node.description || '无描述'}</p>
                  <p>
                    <Tag color={getNodeTypeColor(node.node_type)}>
                      {getNodeTypeName(node.node_type)}
                    </Tag>
                    {node.node_type === 'approval' && (
                      <>
                        {node.approver_role_id && <Tag color="purple">{getApproverInfo(node)}</Tag>}
                        {node.approvers?.map((approver) => (
                          <Tag color="pink" key={approver.id}>
                            {approver.name}
                          </Tag>
                        ))}
                      </>
                    )}
                  </p>
                </div>
              }
            />
          ))}
        </Steps>
      </Card>
    </>
  );
};

export default WorkflowDetail; 