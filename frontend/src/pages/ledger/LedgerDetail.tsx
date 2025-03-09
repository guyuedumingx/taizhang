import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Button, Space, Tag, Divider, message, Spin, Timeline } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { EditOutlined, DownloadOutlined, ClockCircleOutlined, CheckCircleOutlined, SendOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { ApprovalService } from '../../services/ApprovalService';
import { TemplateService } from '../../services/TemplateService';
import { Ledger, AuditLog, Field } from '../../types';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;

const LedgerDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [fields, setFields] = useState<Field[]>([]);

  // 获取台账详情和审计日志
  useEffect(() => {
    if (!id) {
      message.error('台账ID无效');
      navigate('/dashboard/ledgers');
      return;
    }

    if (!hasPermission(PERMISSIONS.LEDGER_VIEW)) {
      message.error('您没有查看台账的权限');
      navigate('/dashboard');
      return;
    }

    const ledgerId = parseInt(id);
    fetchLedgerDetails(ledgerId);
  }, [id, hasPermission, navigate]);

  // 获取台账详情、模板字段和审计日志
  const fetchLedgerDetails = async (ledgerId: number) => {
    setLoading(true);
    try {
      const [ledgerData, logsData] = await Promise.all([
        LedgerService.getLedger(ledgerId),
        ApprovalService.getLedgerAuditLogs(ledgerId)
      ]);

      setLedger(ledgerData);
      setAuditLogs(logsData);

      // 如果有模板ID，获取模板字段
      if (ledgerData.template_id) {
        try {
          const templateData = await TemplateService.getTemplate(ledgerData.template_id);
          setFields(templateData.fields);
        } catch (error) {
          console.error('获取模板字段失败:', error);
        }
      }
    } catch (error) {
      console.error('获取台账详情失败:', error);
      message.error('获取台账详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理导出
  const handleExport = async (format: string) => {
    if (!id) return;
    
    try {
      const blob = await LedgerService.exportLedger(parseInt(id), format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `台账_${id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('导出失败:', error);
      message.error('导出失败');
    }
  };

  // 处理审批提交
  const handleSubmitApproval = async () => {
    if (!id || !ledger) return;
    
    try {
      await ApprovalService.submitLedger(parseInt(id), { comment: '提交审批' });
      message.success('提交审批成功');
      fetchLedgerDetails(parseInt(id));
    } catch (error) {
      console.error('提交审批失败:', error);
      message.error('提交审批失败');
    }
  };

  // 处理审批通过
  const handleApprove = async () => {
    if (!id || !ledger) return;
    
    try {
      await ApprovalService.approveLedger(parseInt(id), { action: 'approve', comment: '审批通过' });
      message.success('审批通过');
      fetchLedgerDetails(parseInt(id));
    } catch (error) {
      console.error('审批失败:', error);
      message.error('审批失败');
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
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('excel')}
              >
                导出
              </Button>
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
            {ledger.status === 'draft' && hasPermission(PERMISSIONS.APPROVAL_SUBMIT) && (
              <Button 
                type="primary" 
                icon={<SendOutlined />}
                onClick={handleSubmitApproval}
              >
                提交审批
              </Button>
            )}
            {ledger.status === 'active' && hasPermission(PERMISSIONS.APPROVAL_APPROVE) && (
              <Button 
                type="primary" 
                icon={<CheckCircleOutlined />}
                onClick={handleApprove}
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
    </>
  );
};

export default LedgerDetail; 