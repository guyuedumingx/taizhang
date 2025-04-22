import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Button, Space, Tag, Divider, message, Spin, Timeline, Modal, Form, Select, Input, Dropdown } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { EditOutlined, DownloadOutlined, ClockCircleOutlined, CheckCircleOutlined, UploadOutlined, DownOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { TemplateService } from '../../services/TemplateService';
import { WorkflowService } from '../../services/WorkflowService';
import { Ledger, AuditLog, Field, Workflow } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import ApproverSelector from '../../components/workflow/ApproverSelector';
import { submitLedgerForApproval } from '../../api/approvals';
import ApprovalModal from '../../components/approval/ApprovalModal';
import { downloadBlobAsFile } from '../../utils/exportUtils';

const { Title, Text } = Typography;

const LedgerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission, user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [fields, setFields] = useState<Field[]>([]);

  // 提交审批相关状态
  const [submitModalVisible, setSubmitModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [nextApproverId, setNextApproverId] = useState<number | undefined>(undefined);
  // 存储下一个节点的ID，用于审批人选择
  const [nextNodeId, setNextNodeId] = useState<number | undefined>(undefined);
  const [submitComment, setSubmitComment] = useState('');
  
  // 模板是否有工作流标志
  const [templateHasWorkflow, setTemplateHasWorkflow] = useState<boolean>(false);

  // 审批处理相关状态
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);

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
      
      // 获取模板关联的工作流
      if (ledger?.template_id) {
        try {
          const template = await TemplateService.getTemplateDetail(ledger.template_id);
          if (template.workflow_id) {
            const bingWorkflow = await WorkflowService.getWorkflow(template.workflow_id);
            if (bingWorkflow) {
              setWorkflow(bingWorkflow);
              
              // 设置默认的下一节点，如果工作流有节点
              if (bingWorkflow.nodes && bingWorkflow.nodes.length > 0) {
                // 排序节点，找到第一个需要审批的节点
                const nodes = [...bingWorkflow.nodes].sort((a, b) => a.order_index - b.order_index).filter(node => node.node_type === 'approval');
                if (nodes.length > 0) {
                  setNextNodeId(nodes[0].id);
                }
              }
              
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

  // 提交审批
  const submitForApproval = async () => {
    let workflowToUse = workflow;
    
    // 如果没有选择工作流，尝试使用台账模板的默认工作流
    if (!workflowToUse && ledger && ledger.template_id) {
      try {
        const template = await TemplateService.getTemplateDetail(ledger.template_id);
        if (template.workflow_id) {
          const defaultWorkflow = await WorkflowService.getWorkflow(template.workflow_id);
          if (defaultWorkflow) {
            workflowToUse = defaultWorkflow;
            message.info(`使用模板工作流: ${defaultWorkflow.name}`);
          }
        }
      } catch (error) {
        console.error('获取工作流失败:', error);
      }
    }
    
    if (!workflowToUse) {
      message.error('无工作流');
      return;
    }
    
    if (nextNodeId && nextApproverId === undefined) {
      message.error('请选择审批人');
      return;
    }
    
    setSubmitting(true);
    try {
      await submitLedgerForApproval(parseInt(id!), {
        workflow_id: workflowToUse.id,
        comment: submitComment,
        next_approver_id: nextApproverId
      });
      message.success('提交审批成功');
      setSubmitModalVisible(false);
      // 重新获取台账信息
      if (id) {
        fetchLedgerDetails(parseInt(id));
      }
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
    setApprovalModalVisible(true);
  };

  // 处理审批成功
  const handleApprovalSuccess = () => {
    setApprovalModalVisible(false);
    // 刷新数据
    if (id) {
      fetchLedgerDetails(parseInt(id));
    }
  };

  // 渲染审计日志
  const renderAuditLogs = () => {
    if (!auditLogs || auditLogs.length === 0) {
      return <Text>暂无审计日志</Text>;
    }
    
    return (
      <Timeline mode="left">
        {auditLogs.map((log, index) => (
          <Timeline.Item 
            key={log.id}
            color={log.action === 'submit' ? 'orange' : log.action === 'approve' ? 'green' : log.action === 'reject' ? 'red' : 'orange'}
          >
            <Space>
              <Text strong>{auditLogs.length - index}</Text>
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
      
      // 使用工具函数下载文件
      const filename = `台账_${id}.${fileExtension}`;
      downloadBlobAsFile(blob, filename);
      
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
            {hasPermission(PERMISSIONS.LEDGER_EDIT)
              && user?.id === ledger.created_by_id 
              && (ledger.approval_status === 'draft' || ledger.approval_status === 'rejected')
              && (
              <Button 
                type="primary" 
                icon={<EditOutlined />} 
                onClick={() => navigate(`/dashboard/ledgers/edit/${id}`)}
              >
                编辑
              </Button>
            )}
            {(ledger.approval_status === 'draft' || ledger.approval_status === 'returned') && hasPermission(PERMISSIONS.LEDGER_SUBMIT) && templateHasWorkflow && (
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
                审批
              </Button>
            )}
          </Space>
        </div>

        <Descriptions bordered column={2}>
          <Descriptions.Item label="台账编号">{ledger.id}</Descriptions.Item>
          <Descriptions.Item label="模板">{ledger.template_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={ledger.status === 'completed' ? 'success' : ledger.status === 'active' ? 'processing' : ledger.status === 'returned' ? 'error' : 'default'}>
              {ledger.status === 'completed' ? '已完成' : ledger.status === 'active' ? '处理中' : ledger.status === 'returned' ? '已退回' : '草稿'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="审批状态">
            <Tag color={ledger.approval_status === 'approved' ? 'success' : ledger.approval_status === 'rejected' ? 'error' : ledger.approval_status === 'pending' ? 'processing' : 'default'}>
              {ledger.approval_status === 'approved' ? '已批准' : ledger.approval_status === 'rejected' ? '已拒绝' : ledger.approval_status === 'pending' ? '审批中' : '草稿'}
            </Tag>
          </Descriptions.Item>
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
          {workflow && (
            <Form.Item label="工作流">
              <Input value={workflow.name} disabled />
            </Form.Item>
          )}
          
          {workflow && workflow.nodes && nextNodeId && (
            <Form.Item required>
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

      {ledger && ledger.active_workflow_instance && (
        <ApprovalModal
          visible={approvalModalVisible}
          onCancel={() => setApprovalModalVisible(false)}
          onSuccess={handleApprovalSuccess}
          ledgerId={ledger.id}
          workflowInstanceId={ledger.active_workflow_instance.id}
          currentNodeId={ledger.active_workflow_instance.current_node_id || undefined}
        />
      )}
    </>
  );
};

export default LedgerDetail; 