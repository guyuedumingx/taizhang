import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Tag, Popconfirm, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { ledgerApi } from '../../api';
import { Ledger } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Search } = Input;

const LedgerList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [searchText, setSearchText] = useState('');

  const fetchLedgers = async () => {
    setLoading(true);
    try {
      const data = await ledgerApi.getLedgers();
      setLedgers(data);
    } catch (error) {
      console.error('获取台账列表失败:', error);
      message.error('获取台账列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedgers();
  }, []);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleDelete = async (id: number) => {
    try {
      await ledgerApi.deleteLedger(id);
      message.success('删除成功');
      fetchLedgers();
    } catch (error) {
      console.error('删除台账失败:', error);
      message.error('删除台账失败');
    }
  };

  const filteredLedgers = ledgers.filter(item => 
    item.name.toLowerCase().includes(searchText.toLowerCase()) ||
    item.description?.toLowerCase().includes(searchText.toLowerCase()) ||
    item.created_by_name?.toLowerCase().includes(searchText.toLowerCase()) ||
    item.team_name?.toLowerCase().includes(searchText.toLowerCase()) ||
    item.template_name?.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns: ColumnsType<Ledger> = [
    {
      title: '台账名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '团队',
      dataIndex: 'team_name',
      key: 'team_name',
    },
    {
      title: '模板',
      dataIndex: 'template_name',
      key: 'template_name',
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
      sorter: (a, b) => a.created_at.localeCompare(b.created_at),
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text: string) => (
        <Tag color={text === 'completed' ? 'success' : text === 'active' ? 'processing' : 'default'}>
          {text === 'completed' ? '已完成' : text === 'active' ? '处理中' : '草稿'}
        </Tag>
      ),
      filters: [
        { text: '草稿', value: 'draft' },
        { text: '处理中', value: 'active' },
        { text: '已完成', value: 'completed' },
      ],
      onFilter: (value, record) => record.status === value.toString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/ledgers/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/ledgers/edit/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_EDIT)}
          />
          <Popconfirm
            title="确定要删除这个台账吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.LEDGER_DELETE)}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.LEDGER_DELETE)}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>台账列表</Title>
          <Space>
            <Search
              placeholder="搜索台账"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/ledgers/new')}
              disabled={!hasPermission(PERMISSIONS.LEDGER_CREATE)}
            >
              新建台账
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredLedgers}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>
    </div>
  );
};

export default LedgerList; 