import React from 'react';
import { Table, Button, Card, Typography, Tag } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { Ledger } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';

const { Title } = Typography;

interface RecentLedgersTableProps {
  ledgers: Ledger[];
  loading: boolean;
}

const RecentLedgersTable: React.FC<RecentLedgersTableProps> = ({ ledgers, loading }) => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();

  const columns = [
    {
      title: '台账名称',
      dataIndex: 'name',
      key: 'name',
      width: '30%',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (text: string) => (
        <Tag color={text === 'completed' ? 'success' : text === 'active' ? 'processing' : text === 'returned' ? 'error' : 'default'}>
          {text === 'completed' ? '已完成' : text === 'active' ? '处理中' : text === 'returned' ? '已退回' : '草稿'}
        </Tag>
      ),
      filters: [
        { text: '草稿', value: 'draft' },
        { text: '处理中', value: 'active' },
        { text: '已完成', value: 'completed' },
        { text: '已退回', value: 'returned' },
      ],
      onFilter: (value, record) => record.status === value.toString(),
    },
    {
      title: '团队',
      dataIndex: 'team_name',
      key: 'team_name',
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Ledger) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />}
          onClick={() => navigate(`/dashboard/ledgers/${record.id}`)}
          disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="page-header">
        <Title level={4} className="page-title">最近台账</Title>
        <Button type="link" onClick={() => navigate('/dashboard/ledgers')}>
          查看全部
        </Button>
      </div>

      <Card className="dashboard-card">
        <Table
          columns={columns}
          dataSource={ledgers}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </>
  );
};

export default RecentLedgersTable; 