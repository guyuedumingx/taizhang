import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Input, Typography, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { ApprovalService } from '../../services/ApprovalService';
import { WorkflowService } from '../../services/WorkflowService';
import { getWorkflowInstance } from '../../api/workflow_instances';
import ApproverSelector from '../workflow/ApproverSelector';

const { Text } = Typography;

export interface ApprovalModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  ledgerId?: number;
  workflowInstanceId?: number;
  taskId?: number;
  currentNodeId?: number;
}

const ApprovalModal: React.FC<ApprovalModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  ledgerId,
  workflowInstanceId,
  taskId,
  currentNodeId,
}) => {
  const [approving, setApproving] = useState(false);
  const [approvalComment, setApprovalComment] = useState('');
  const [nextNodeId, setNextNodeId] = useState<number | undefined>(undefined);
  const [nextApproverId, setNextApproverId] = useState<number | undefined>(undefined);

  // 多人审批相关状态
  const [currentNodeMultiApproveType, setCurrentNodeMultiApproveType] = useState<string>('any');
  const [currentNodeNeedSelectNextApprover, setCurrentNodeNeedSelectNextApprover] = useState<boolean>(false);
  const [currentNodeApprovedCount, setCurrentNodeApprovedCount] = useState<number>(0);
  const [currentNodeTotalApprovers, setCurrentNodeTotalApprovers] = useState<number>(0);

  // 当对话框显示时加载工作流节点信息
  useEffect(() => {
    if (visible && workflowInstanceId && currentNodeId) {
      loadWorkflowNodeInfo(workflowInstanceId, currentNodeId);
    }
  }, [visible, workflowInstanceId, currentNodeId]);

  // 获取工作流节点信息
  const loadWorkflowNodeInfo = async (instanceId: number, nodeId: number) => {
    try {
      // 重置状态
      setNextApproverId(undefined);
      
      // 获取工作流实例信息
      const instanceData = await getWorkflowInstance(instanceId);
      if (!instanceData) return;
      
      const workflowId = instanceData.workflow_id;
      // 获取工作流详情
      const workflowData = await WorkflowService.getWorkflow(workflowId);
      if (!workflowData || !workflowData.nodes) return;

      const instanceNode = instanceData.nodes.find(node => node.id === nodeId);

      // 找到当前节点
      const currentNode = workflowData.nodes.find(node => node.id === instanceNode.workflow_node_id);
      if (!currentNode) return;
      // 设置当前节点的审批模式
      setCurrentNodeMultiApproveType(currentNode.multi_approve_type || 'any');
      
      // 获取当前节点已审批的数量
      if (currentNode.approvers && Array.isArray(currentNode.approvers)) {
        setCurrentNodeTotalApprovers(currentNode.approvers.length);
        
        // 获取已审批人数 (这里需要实际数据支持)
        setCurrentNodeApprovedCount(instanceData.approved_count || 0);
      }
      // 获取下一个节点
      const nextNodes = workflowData.nodes
        .filter(node => node.order_index > currentNode.order_index)
        .sort((a, b) => a.order_index - b.order_index);
      if (nextNodes.length > 0) {
        const nextNode = nextNodes[0];
        setNextNodeId(nextNode.id);
        if (nextNode.approvers) {
          if (nextNode.approvers.length === 1){
            // 如果只有一个审批人，自动选择
            setNextApproverId(nextNode.approvers[0].id);
          } else if(nextNode.approvers.length > 1) {
            setCurrentNodeNeedSelectNextApprover(true);
          } else {
            setCurrentNodeNeedSelectNextApprover(false);
          }
        }
      }
    } catch (error) {
      console.error('获取工作流节点信息失败:', error);
      message.error('获取工作流节点信息失败');
    }
  };

  // 处理审批
  const processApproval = async (approvalAction: 'approve' | 'reject') => {
    // 验证：如果需要选择下一个审批人但没有选择
    if (currentNodeNeedSelectNextApprover && !nextApproverId) {
      message.error('请选择下一步审批人');
      return;
    }
    
    setApproving(true);
    try {
      const approvalData = {
        action: approvalAction,
        comment: approvalComment,
        next_approver_id: currentNodeNeedSelectNextApprover ? nextApproverId : undefined
      };
      
      // 根据传入的参数判断调用方式
      if (workflowInstanceId && taskId) {
        //TODO: TaskList页面调用方式 taskId 是 ledgerId 
        await ApprovalService.approveLedger(taskId, approvalData);
      } else if (ledgerId && workflowInstanceId) {
        //TODO: LedgerDetail页面调用方式
        await ApprovalService.approveLedger(ledgerId, approvalData);
      } else {
        throw new Error('缺少必要参数');
      }
      
      message.success(`台账审批${approvalAction === 'approve' ? '通过' : '拒绝'}成功`);
      onSuccess();
    } catch (error) {
      console.error('处理审批失败:', error);
      message.error('处理审批失败，请稍后重试');
    } finally {
      setApproving(false);
    }
  };

  return (
    <Modal
      title="处理审批"
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="reject"
          danger
          loading={approving}
          onClick={() => {
            processApproval('reject');
          }}
          icon={<CloseCircleOutlined />}
        >
          拒绝
        </Button>,
        <Button
          key="approve"
          type="primary"
          loading={approving}
          onClick={() => {
            processApproval('approve');
          }}
          disabled={currentNodeNeedSelectNextApprover && !nextApproverId}
          icon={<CheckCircleOutlined />}
        >
          通过
        </Button>
      ]}
    >
      <Form layout="vertical">
        <div style={{ marginBottom: 16 }}>
          <Typography.Text type="secondary">
            请对该台账进行审批。如果通过，将流转到下一审批步骤；如果拒绝，审批流程将终止。
          </Typography.Text>
        </div>
        
        {/* 显示当前节点审批状态 */}
        {currentNodeMultiApproveType === 'all' && currentNodeTotalApprovers > 1 && (
          <div style={{ marginBottom: 16 }}>
            <Typography.Text>
              当前节点审批状态：已有 {currentNodeApprovedCount} 人审批通过，
              共需要 {currentNodeTotalApprovers} 人全部通过
            </Typography.Text>
          </div>
        )}
        
        {/* 根据需要显示审批人选择器 */}
        {currentNodeNeedSelectNextApprover && (
          <Form.Item required style={{ marginTop: 16 }}>
            <ApproverSelector
              nodeId={nextNodeId || 0}
              value={nextApproverId}
              onChange={(value) => setNextApproverId(value as number)}
              required={true}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">当前工作流节点需要选择下一步审批人</Text>
            </div>
          </Form.Item>
        )}
        
        <Form.Item label="审批意见" style={{ marginTop: 16 }}>
          <Input.TextArea
            rows={4}
            value={approvalComment}
            onChange={(e) => setApprovalComment(e.target.value)}
            placeholder="请输入审批意见"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ApprovalModal; 