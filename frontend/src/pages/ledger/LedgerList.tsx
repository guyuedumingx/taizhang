import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Tag, Popconfirm, message, Dropdown } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { Ledger } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Search } = Input;

const LedgerList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission, token } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [searchText, setSearchText] = useState('');

  const fetchLedgers = async () => {
    // 检查是否已登录
    if (!token) {
      navigate('/login');
      return;
    }
    
    setLoading(true);
    try {
      const data = await LedgerService.getLedgers();
      setLedgers(data);
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`获取台账列表失败: ${error.message}`);
      } else {
        message.error('获取台账列表失败');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedgers();
  }, [token, navigate]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleDelete = async (id: number) => {
    try {
      await LedgerService.deleteLedger(id);
      message.success('删除成功');
      fetchLedgers();
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`删除失败: ${error.message}`);
      } else {
        message.error('删除失败');
      }
    }
  };

  // 处理导出单个台账
  const handleExport = async (id: number, format: string) => {
    try {
      const blob = await LedgerService.exportLedger(id, format);
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `台账_${id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`导出失败: ${error.message}`);
      } else {
        message.error('导出失败');
      }
    }
  };

  // 处理导出所有台账
  const handleExportAll = async (format: string) => {
    try {
      const blob = await LedgerService.exportAllLedgers(format);
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `台账_全部.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`导出失败: ${error.message}`);
      } else {
        message.error('导出失败');
      }
    }
  };

  const filteredLedgers = ledgers.filter(item => 
    item.name.toLowerCase().includes(searchText.toLowerCase()) ||
    (item.description && item.description.toLowerCase().includes(searchText.toLowerCase())) ||
    (item.created_by_name && item.created_by_name.toLowerCase().includes(searchText.toLowerCase())) ||
    (item.team_name && item.team_name.toLowerCase().includes(searchText.toLowerCase())) ||
    (item.template_name && item.template_name.toLowerCase().includes(searchText.toLowerCase()))
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
            onClick={() => navigate(`/dashboard/ledgers/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/dashboard/ledgers/edit/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_EDIT)}
          />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'excel',
                  label: 'Excel格式',
                  onClick: () => handleExport(record.id, 'excel')
                },
                {
                  key: 'csv',
                  label: 'CSV格式',
                  onClick: () => handleExport(record.id, 'csv')
                },
                {
                  key: 'txt',
                  label: 'TXT格式',
                  onClick: () => handleExport(record.id, 'txt')
                }
              ]
            }}
            disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT)}
          >
            <Button
              type="text"
              icon={<DownloadOutlined />}
              disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT)}
            />
          </Dropdown>
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
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'excel',
                    label: '导出为Excel',
                    onClick: () => handleExportAll('excel')
                  },
                  {
                    key: 'csv',
                    label: '导出为CSV',
                    onClick: () => handleExportAll('csv')
                  },
                  {
                    key: 'txt',
                    label: '导出为TXT',
                    onClick: () => handleExportAll('txt')
                  }
                ]
              }}
              disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT) || ledgers.length === 0}
            >
              <Button 
                type="default" 
                icon={<DownloadOutlined />}
                disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT) || ledgers.length === 0}
              >
                导出
              </Button>
            </Dropdown>
            {hasPermission(PERMISSIONS.LEDGER_CREATE) && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/dashboard/ledgers/new')}
              >
                新建台账
              </Button>
            )}
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredLedgers}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showQuickJumper: true,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>
    </div>
  );
};

export default LedgerList; 