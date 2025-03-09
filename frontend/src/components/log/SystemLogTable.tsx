import React from 'react';
import { Table, Tag, Typography, Space, TablePaginationConfig } from 'antd';
import { SystemLog } from '../../types';
import { LogService } from '../../services/LogService';

const { Text } = Typography;

interface SystemLogTableProps {
  logs: SystemLog[];
  loading: boolean;
  pagination: TablePaginationConfig;
  onChange: (pagination: TablePaginationConfig) => void;
}

const SystemLogTable: React.FC<SystemLogTableProps> = ({
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
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level: string) => {
        const { color, label } = LogService.formatLogLevel(level);
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 120,
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
      render: (text: string, record: SystemLog) => (
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
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      render: (text: string) => (
        <div style={{ wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
          {text}
        </div>
      ),
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

export default SystemLogTable; 