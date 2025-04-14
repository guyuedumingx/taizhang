import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Button, Space, Tag, Divider, message, Spin, Timeline, Modal, Form, Select, Input, Dropdown } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { EditOutlined, DownloadOutlined, ClockCircleOutlined, CheckCircleOutlined, UploadOutlined, DownOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS, API_BASE_URL } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { TemplateService } from '../../services/TemplateService';
import { WorkflowService } from '../../services/WorkflowService';
import { Ledger, AuditLog, Field, Workflow, WorkflowNode } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import ApproverSelector from '../../components/workflow/ApproverSelector';
import axios from 'axios';

const { Title, Text } = Typography;

const LedgerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [fields, setFields] = useState<Field[]>([]);

  // 提交审批相关状态
  const [submitModalVisible, setSubmitModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [nextApproverId, setNextApproverId] = useState<number | undefined>(undefined);
  const [nextNodeId, setNextNodeId] = useState<number | undefined>(undefined);
  const [submitComment, setSubmitComment] = useState('');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  
  // 模板是否有工作流标志
  const [templateHasWorkflow, setTemplateHasWorkflow] = useState<boolean>(false);

  // 审批处理相关状态
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approvalAction, setApprovalAction] = useState<'approve' | 'reject'>('approve');
  const [approvalComment, setApprovalComment] = useState('');
  const [nextApprovalNodeId, setNextApprovalNodeId] = useState<number | undefined>(undefined);
  const [nextApprovalApproverId, setNextApprovalApproverId] = useState<number | undefined>(undefined);

  // 添加或修改以下状态变量和函数处理新的工作流功能
  const [currentNodeMultiApproveType, setCurrentNodeMultiApproveType] = useState<string>('any');
  const [currentNodeNeedSelectNextApprover, setCurrentNodeNeedSelectNextApprover] = useState<boolean>(false);
  const [currentNodeApprovedCount, setCurrentNodeApprovedCount] = useState<number>(0);
  const [currentNodeTotalApprovers, setCurrentNodeTotalApprovers] = useState<number>(0);

  // 组件加载时获取台账详情
  useEffect(() => {
    if (id) {
      console.log('获取台账详情:', id);
      fetchLedgerDetails(parseInt(id));
    }
  }, [id]);

  // 台账详情加载完成后检查是否有关联工作流
  useEffect(() => {
    if (ledger && !loading) {
      checkTemplateWorkflow();
    }
  }, [ledger, loading]);

  // 从localStorage获取token
  const getToken = () => {
    return localStorage.getItem('auth-storage')
      ? JSON.parse(localStorage.getItem('auth-storage') || '{}').state?.token
      : null;
  };

  // 获取台账详情和审计日志
  const fetchLedgerDetails = async (ledgerId: number) => {
    setLoading(true);
    try {
      console.log(`正在获取台账ID=${ledgerId}的详情和审计日志...`);
      const [ledgerData, logsData] = await Promise.all([
        LedgerService.getLedger(ledgerId),
        LedgerService.getLedgerAuditLogs(ledgerId)
      ]);
      
      console.log('台账详情:', ledgerData);
      console.log('审计日志:', logsData);
      
      setLedger(ledgerData);
      setAuditLogs(logsData);
      
      // 如果有模板ID，获取模板字段
      if (ledgerData.template_id) {
        console.log(`获取模板ID=${ledgerData.template_id}的字段...`);
        const templateData = await TemplateService.getTemplateDetail(ledgerData.template_id);
        console.log('模板字段:', templateData.fields);
        setFields(templateData.fields);
      }
    } catch (error) {
      console.error('获取台账详情失败:', error);
      message.error('获取台账详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 检查模板是否关联了工作流
  const checkTemplateWorkflow = async () => {
    if (!ledger) return;
    
    try {
      // 如果台账已经关联了工作流
      if (ledger.active_workflow_instance?.workflow_id) {
        setTemplateHasWorkflow(true);
        return;
      }
      
      // 查询模板是否关联了工作流
      if (ledger.template_id) {
        const template = await TemplateService.getTemplateDetail(ledger.template_id);
        if (template.workflow_id) {
          setTemplateHasWorkflow(true);
        } else {
          setTemplateHasWorkflow(false);
        }
      } else {
        setTemplateHasWorkflow(false);
      }
    } catch (error) {
      console.error('检查模板工作流失败:', error);
      setTemplateHasWorkflow(false);
    }
  };

  // 获取可用工作流
  const fetchWorkflows = async () => {
    try {
      // 如果台账有关联工作流，直接使用
      // if (ledger?.workflow_id) {
      //   const workflowData = await WorkflowService.getWorkflow(ledger.workflow_id);
      //   setWorkflow(workflowData);
      //   setWorkflows([workflowData]);
      //   fetchWorkflowDetail(workflowData.id);
      //   return;
      // }
      
      // 获取模板关联的工作流
      if (ledger?.template_id) {
        try {
          const template = await TemplateService.getTemplateDetail(ledger.template_id);
          if (template.workflow_id) {
            const bingWorkflow = await WorkflowService.getWorkflow(template.workflow_id);
            if (bingWorkflow) {
              setWorkflow(bingWorkflow);
              setWorkflows([bingWorkflow]);
              fetchWorkflowDetail(bingWorkflow.id);
              return;
            }
          }
        } catch (error) {
          console.error('获取模板工作流失败:', error);
        }
      }
    } catch (error) {
      console.error('获取工作流列表失败:', error);
      message.error('获取工作流列表失败');
    }
  };

  // 获取工作流详情
  const fetchWorkflowDetail = async (workflowId: number) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/workflows/${workflowId}`, {
        headers: {
          Authorization: `Bearer ${getToken()}`
        }
      });
      
      console.log('获取工作流详情原始返回数据:', response.data);
      
      // 处理可能的嵌套数据结构
      let workflowData;
      if (response.data && typeof response.data === 'object') {
        if ('item' in response.data && response.data.item) {
          console.log('从嵌套数据中提取工作流详情');
          workflowData = response.data.item;
        } else if ('id' in response.data) {
          workflowData = response.data;
        } else {
          console.error('无法识别工作流数据格式:', response.data);
          message.error('无法识别工作流数据格式');
          return;
        }
      } else {
        console.error('获取工作流详情返回格式不正确:', response.data);
        message.error('获取工作流详情返回格式不正确');
        return;
      }
      
      setWorkflow(workflowData);
      
      // 获取开始节点的下一个节点
      if (workflowData.nodes && workflowData.nodes.length > 0) {
        const startNode = workflowData.nodes.find((node: WorkflowNode) => node.node_type === 'start');
        if (startNode) {
          const nextNodes = workflowData.nodes
            .filter((node: WorkflowNode) => node.order_index > startNode.order_index)
            .sort((a: WorkflowNode, b: WorkflowNode) => a.order_index - b.order_index);
          
          if (nextNodes.length > 0) {
            setNextNodeId(nextNodes[0].id);
            // 如果只有一个审批人或者不需要选择，自动选择
            if (nextNodes[0].approvers && nextNodes[0].approvers.length === 1 && !nextNodes[0].need_select_next_approver) {
              setNextApproverId(nextNodes[0].approvers[0].id);
            }
          }
        }
      }
    } catch (error) {
      console.error('获取工作流详情失败:', error);
      message.error('获取工作流详情失败');
    }
  };

  // 提交审批
  const submitForApproval = async () => {
    let workflowToUse = workflow;
    
    // 如果没有选择工作流，尝试使用台账模板的默认工作流
    if (!workflowToUse && ledger && ledger.template_id) {
      try {
        const template = await TemplateService.getTemplateDetail(ledger.template_id);
        if (template.workflow_id) {
          const defaultWorkflow = await WorkflowService.getWorkflow(template.default_workflow_id);
          if (defaultWorkflow) {
            workflowToUse = defaultWorkflow;
            message.info(`使用模板工作流: ${defaultWorkflow.name}`);
          }
        }
      } catch (error) {
        console.error('获取模板工作流失败:', error);
      }
    }
    
    if (!workflowToUse) {
      message.error('请选择工作流');
      return;
    }
    
    if (nextNodeId && nextApproverId === undefined) {
      message.error('请选择审批人');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(
        `${API_BASE_URL}/ledgers/${id}/submit`,
        {
          workflow_id: workflowToUse.id,
          comment: submitComment,
          next_approver_id: nextApproverId
        },
        {
          headers: {
            Authorization: `Bearer ${getToken()}`
          }
        }
      );
      
      message.success('提交审批成功');
      setSubmitModalVisible(false);
      // 重新获取台账信息
      if (id) {
        fetchLedgerDetails(parseInt(id));
      }
    } catch (error) {
      console.error('提交审批失败:', error);
      message.error('提交审批失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 打开提交审批对话框
  const showSubmitModal = () => {
    // 获取可用工作流
    fetchWorkflows();
    setSubmitModalVisible(true);
  };

  // 打开处理审批对话框
  const showApprovalModal = () => {
    // 清空状态
    setNextApprovalApproverId(undefined);
    
    // 获取下一个节点
    if (ledger?.active_workflow_instance?.current_node_id) {
      const currentNodeId = ledger.active_workflow_instance.current_node_id;
      const workflowId = ledger.active_workflow_instance.workflow_id;
      
      // 使用 WorkflowService 获取工作流详情
      WorkflowService.getWorkflow(workflowId)
        .then(workflowData => {
          console.log('获取审批工作流:', workflowData);
          
          const currentNode = workflowData.nodes.find((node: WorkflowNode) => node.id === currentNodeId);
          
          if (currentNode) {
            // 设置当前节点的审批模式
            setCurrentNodeMultiApproveType(currentNode.multi_approve_type || 'any');
            setCurrentNodeNeedSelectNextApprover(currentNode.need_select_next_approver || false);
            
            // 获取当前节点已审批的数量
            if (currentNode.approvers && Array.isArray(currentNode.approvers)) {
              setCurrentNodeTotalApprovers(currentNode.approvers.length);
              
              // 从审计日志获取已审批人数
              const approvedUsers = new Set(
                auditLogs
                  .filter(log => log.action === 'approve')
                  .map(log => log.user_id)
              );
              setCurrentNodeApprovedCount(approvedUsers.size);
            }
            
            const nextNodes = workflowData.nodes
              .filter((node: WorkflowNode) => node.order_index > currentNode.order_index)
              .sort((a: WorkflowNode, b: WorkflowNode) => a.order_index - b.order_index);
            
            if (nextNodes.length > 0) {
              const nextNode = nextNodes[0];
              setNextApprovalNodeId(nextNode.id);
              
              // 检查下一节点审批人选择需求
              if (nextNode.need_select_next_approver) {
                setCurrentNodeNeedSelectNextApprover(true);
                // 如果需要选择，则不自动设置审批人，等待用户选择
              } else if (nextNode.approvers && nextNode.approvers.length === 1) {
                // 如果只有一个审批人，自动选择
                setNextApprovalApproverId(nextNode.approvers[0].id);
              }
            }
          }
        })
        .catch(error => {
          console.error('获取工作流详情失败:', error);
          message.error('获取工作流详情失败');
        });
    }
    
    setApprovalModalVisible(true);
  };

  // 处理审批
  const processApproval = async () => {
    if (!id) return;
    
    // 验证：如果需要选择下一个审批人但没有选择
    if (currentNodeNeedSelectNextApprover && !nextApprovalApproverId) {
      message.error('请选择下一步审批人');
      return;
    }
    
    setApproving(true);
    try {
      const approvalData = {
        action: approvalAction,
        comment: approvalComment,
        next_approver_id: currentNodeNeedSelectNextApprover ? nextApprovalApproverId : undefined
      };
      
      // 使用WorkflowService代替直接的api调用
      await WorkflowService.processApproval(parseInt(id), approvalData);
      
      message.success(`台账审批${approvalAction === 'approve' ? '通过' : '拒绝'}成功`);
      setApprovalModalVisible(false);
      fetchLedgerDetails(parseInt(id)); // 重新获取台账数据
    } catch (error) {
      console.error('处理审批失败:', error);
      message.error('处理审批失败，请稍后重试');
    } finally {
      setApproving(false);
    }
  };

  // 渲染审计日志
  const renderAuditLogs = () => {
    if (!auditLogs || auditLogs.length === 0) {
      return <Text>暂无审计日志</Text>;
    }
    
    return (
      <Timeline mode="left">
        {auditLogs.map(log => (
          <Timeline.Item 
            key={log.id}
            color={log.action === 'create' ? 'green' : log.action === 'approve' ? 'blue' : 'orange'}
          >
            <Space>
              <Text strong>{log.user_id}</Text>
              <Text>{log.action}</Text>
              {log.comment && <Text type="secondary">{log.comment}</Text>}
            </Space>
          </Timeline.Item>
        ))}
      </Timeline>
    );
  };

  // 渲染字段值
  const renderFieldValue = (key: string, value: unknown) => {
    const field = fields.find(f => f.name === key);
    if (!field) return String(value);
    
    if (field.type === 'boolean') {
      return <Tag color="blue">{value ? '是' : '否'}</Tag>;
    }
    
    return String(value);
  };

  // 处理导出
  const handleExport = async (format: string) => {
    if (!id) return;
    
    try {
      message.loading({ content: '正在导出...', key: 'export' });
      const blob = await LedgerService.exportLedger(parseInt(id), format);
      
      // 检查服务器返回的内容类型
      if (blob.type.includes('json')) {
        // 如果返回的是JSON（可能是错误信息），转换成文本并显示
        const text = await blob.text();
        const response = JSON.parse(text);
        message.error({ content: response.detail || '导出失败', key: 'export' });
        return;
      }
      
      // 根据格式确定文件扩展名
      let fileExtension = format;
      if (format.toLowerCase() === 'excel') {
        fileExtension = 'xlsx';
      }
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // 使用默认命名
      const filename = `台账_${id}.${fileExtension}`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success({ content: '导出成功', key: 'export' });
    } catch (error) {
      console.error('导出失败:', error);
      message.error({ content: '导出失败，请重试', key: 'export' });
    }
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>加载中...</div>
        </div>
      </Card>
    );
  }

  if (!ledger) {
    return <Card><Text>台账不存在或已被删除</Text></Card>;
  }

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '台账管理', path: '/dashboard/ledgers' },
          { title: ledger.name || `台账 #${ledger.id}` }
        ]}
      />
      
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>{ledger.name}</Title>
          <Space>
            {hasPermission(PERMISSIONS.LEDGER_EXPORT) && (
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'excel',
                      label: '导出为Excel',
                      onClick: () => handleExport('excel')
                    },
                    {
                      key: 'csv',
                      label: '导出为CSV',
                      onClick: () => handleExport('csv')
                    },
                    {
                      key: 'txt',
                      label: '导出为TXT',
                      onClick: () => handleExport('txt')
                    }
                  ]
                }}
              >
                <Button icon={<DownloadOutlined />}>
                  导出 <DownOutlined />
                </Button>
              </Dropdown>
            )}
            {hasPermission(PERMISSIONS.LEDGER_EDIT) && (
              <Button 
                type="primary" 
                icon={<EditOutlined />} 
                onClick={() => navigate(`/dashboard/ledgers/edit/${id}`)}
              >
                编辑
              </Button>
            )}
            {ledger.status === 'draft' && hasPermission(PERMISSIONS.LEDGER_SUBMIT) && templateHasWorkflow && (
              <Button 
                type="primary" 
                icon={<UploadOutlined />} 
                onClick={showSubmitModal}
              >
                提交审批
              </Button>
            )}
            {ledger.status === 'active' && hasPermission(PERMISSIONS.APPROVAL_APPROVE) && (
              <Button 
                type="primary" 
                icon={<CheckCircleOutlined />}
                onClick={showApprovalModal}
              >
                审批通过
              </Button>
            )}
          </Space>
        </div>

        <Descriptions bordered column={2}>
          <Descriptions.Item label="台账编号">{ledger.id}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={ledger.status === 'completed' ? 'success' : ledger.status === 'active' ? 'processing' : 'default'}>
              {ledger.status === 'completed' ? '已完成' : ledger.status === 'active' ? '处理中' : '草稿'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="模板">{ledger.template_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="所属团队">{ledger.team_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建人">{ledger.created_by_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{ledger.created_at ? new Date(ledger.created_at).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="最后更新" span={2}>
            {ledger.updated_at ? (
              <Space>
                <ClockCircleOutlined />
                <span>{new Date(ledger.updated_at).toLocaleString()}</span>
                {ledger.updated_by_name && <span>- {ledger.updated_by_name}</span>}
              </Space>
            ) : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {ledger.description || '-'}
          </Descriptions.Item>
        </Descriptions>

        {ledger.data && Object.keys(ledger.data).length > 0 && (
          <>
            <Divider orientation="left">台账数据</Divider>
            <Descriptions bordered column={2}>
              {Object.entries(ledger.data).map(([key, value]) => (
                <Descriptions.Item key={key} label={
                  fields.find(f => f.name === key)?.label || key
                }>
                  {renderFieldValue(key, value)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}

        <Divider orientation="left">审计日志</Divider>
        {renderAuditLogs()}
      </Card>

      {/* 提交审批对话框 */}
      <Modal
        title="提交审批"
        open={submitModalVisible}
        onCancel={() => setSubmitModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setSubmitModalVisible(false)}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={submitting}
            onClick={submitForApproval}
            disabled={!workflow}
          >
            提交
          </Button>
        ]}
      >
        <Form layout="vertical">
          {workflows.length > 1 ? (
            <Form.Item label="选择工作流" required>
              <Select
                placeholder="请选择工作流"
                value={workflow?.id}
                onChange={(value) => {
                  const selectedWorkflow = workflows.find(w => w.id === value) || null;
                  setWorkflow(selectedWorkflow);
                  if (selectedWorkflow) {
                    fetchWorkflowDetail(selectedWorkflow.id);
                  }
                }}
              >
                {workflows.map(w => (
                  <Select.Option key={w.id} value={w.id}>
                    {w.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          ) : workflows.length === 1 ? (
            <Form.Item label="工作流">
              <Input value={workflows[0].name} disabled />
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">使用模板关联的默认工作流</Text>
              </div>
            </Form.Item>
          ) : null}
          
          {workflow && workflow.nodes && nextNodeId && 
           workflow.nodes.some(node => node.id === nextNodeId && node.need_select_next_approver) && (
            <Form.Item label="选择审批人" required>
              <ApproverSelector
                nodeId={nextNodeId}
                value={nextApproverId}
                onChange={(approverId: number | number[]) => {
                  if (typeof approverId === 'number') {
                    setNextApproverId(approverId);
                  }
                }}
              />
            </Form.Item>
          )}
          
          <Form.Item label="审批说明">
            <Input.TextArea
              rows={4}
              value={submitComment}
              onChange={(e) => setSubmitComment(e.target.value)}
              placeholder="请输入审批说明"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 处理审批对话框 */}
      <Modal
        title="处理审批"
        open={approvalModalVisible}
        onCancel={() => setApprovalModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setApprovalModalVisible(false)}>
            取消
          </Button>,
          <Button
            key="reject"
            danger
            loading={approving && approvalAction === 'reject'}
            onClick={() => {
              setApprovalAction('reject');
              processApproval();
            }}
          >
            拒绝
          </Button>,
          <Button
            key="approve"
            type="primary"
            loading={approving && approvalAction === 'approve'}
            onClick={() => {
              setApprovalAction('approve');
              processApproval();
            }}
            disabled={currentNodeNeedSelectNextApprover && !nextApprovalApproverId}
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
            <Form.Item label="选择下一步审批人" required style={{ marginTop: 16 }}>
              <ApproverSelector
                nodeId={nextApprovalNodeId || 0}
                value={nextApprovalApproverId}
                onChange={(value) => setNextApprovalApproverId(value as number)}
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
    </>
  );
};

export default LedgerDetail; 