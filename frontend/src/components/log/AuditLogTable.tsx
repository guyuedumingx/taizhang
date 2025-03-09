import React from 'react';
import { Table, Tag, Typography, Space, TablePaginationConfig } from 'antd';
import { AuditLog } from '../../types';
import { LogService } from '../../services/LogService';

const { Text } = Typography;

interface AuditLogTableProps {
  logs: AuditLog[];
  loading: boolean;
  pagination: TablePaginationConfig;
  onChange: (pagination: TablePaginationConfig) => void;
}

const AuditLogTable: React.FC<AuditLogTableProps> = ({
  logs,
  loading,
  pagination,
  onChange,
}) => {
  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => LogService.formatDateTime(text),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => {
        const { color, label } = LogService.formatActionType(action);
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '用户',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 120,
      render: (text: string, record: AuditLog) => (
        <Space direction="vertical" size={0}>
          <Text>{text}</Text>
          {record.user_id && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              ID: {record.user_id}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '台账',
      dataIndex: 'ledger_name',
      key: 'ledger_name',
      width: 150,
      render: (text: string, record: AuditLog) => (
        record.ledger_id ? (
          <Space direction="vertical" size={0}>
            <Text>{text || '未命名台账'}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              ID: {record.ledger_id}
            </Text>
          </Space>
        ) : null
      ),
    },
    {
      title: '状态变更',
      key: 'status_change',
      width: 180,
      render: (_: unknown, record: AuditLog) => (
        record.status_before || record.status_after ? (
          <Space>
            {record.status_before && (
              <Tag color="orange">{record.status_before}</Tag>
            )}
            {(record.status_before && record.status_after) && (
              <Text type="secondary">→</Text>
            )}
            {record.status_after && (
              <Tag color="green">{record.status_after}</Tag>
            )}
          </Space>
        ) : null
      ),
    },
    {
      title: '备注',
      dataIndex: 'comment',
      key: 'comment',
      render: (text: string) => text || '-',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={logs.map(log => ({ ...log, key: log.id }))}
      pagination={pagination}
      onChange={onChange}
      loading={loading}
      scroll={{ x: 1200 }}
      size="middle"
    />
  );
};

export default AuditLogTable; 