import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Tag, Popconfirm, message, Dropdown, Menu } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';
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
  const { hasPermission, token } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [searchText, setSearchText] = useState('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

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

  // 导出所有台账
  const handleExportAll = async (format: string) => {
    try {
      // 构建URL，如果有模板筛选，则添加参数
      let apiUrl = `/api/v1/ledgers/export-all?format=${format}`;
      if (selectedTemplateId) {
        apiUrl += `&template_id=${selectedTemplateId}`;
      }
      
      // 使用fetch API直接下载文件
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '导出失败');
      }
      
      // 获取文件名
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `台账列表.${format}`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/["']/g, '');
        }
      }
      
      // 创建Blob对象
      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // 清理
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
      
      message.success(`台账列表已导出为${format.toUpperCase()}格式`);
    } catch (error) {
      console.error('导出台账列表失败:', error);
      message.error('导出台账列表失败: ' + (error as Error).message);
    }
  };
  
  // 导出菜单
  const exportMenu = (
    <Menu
      items={[
        {
          key: 'excel',
          label: 'Excel格式',
          onClick: () => handleExportAll('excel')
        },
        {
          key: 'csv',
          label: 'CSV格式',
          onClick: () => handleExportAll('csv')
        },
        {
          key: 'txt',
          label: 'TXT格式',
          onClick: () => handleExportAll('txt')
        }
      ]}
    />
  );

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>台账列表</Title>
          <Space>
            <Dropdown overlay={exportMenu} placement="bottomRight">
              <Button icon={<DownloadOutlined />}>导出</Button>
            </Dropdown>
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