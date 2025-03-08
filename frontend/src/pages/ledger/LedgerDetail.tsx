import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Button, Space, Tag, Divider, Table, message, Popconfirm, Dropdown } from 'antd';
import { EditOutlined, DeleteOutlined, ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { ledgerApi } from '../../api';
import { Ledger } from '../../types';

const { Title } = Typography;

interface LedgerField {
  id: string;
  name: string;
  value: string;
}

interface LedgerDetail {
  id: number;
  title: string;
  department: string;
  teamName: string;
  description: string;
  date: string;
  status: string;
  createdBy: string;
  createdAt: string;
  updatedBy: string;
  updatedAt: string;
  fields: LedgerField[];
}

const LedgerDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { hasPermission, token } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<LedgerDetail | null>(null);

  const fetchLedger = async () => {
    // 检查是否已登录
    if (!token) {
      navigate('/login');
      return;
    }
    
    setLoading(true);
    try {
      const data = await ledgerApi.getLedger(Number(id));
      
      // 将 API 返回的数据转换为 LedgerDetail 类型
      const ledgerDetail: LedgerDetail = {
        id: data.id,
        title: data.name || '',
        department: data.team_id ? '财务部' : '', // 假设的部门
        teamName: data.team_name || '',
        description: data.description || '',
        date: data.created_at ? new Date(data.created_at).toLocaleDateString() : '',
        status: data.status || '',
        createdBy: data.created_by_name || '',
        createdAt: data.created_at || '',
        updatedBy: data.updated_by_name || '',
        updatedAt: data.updated_at || '',
        fields: [] // 假设的字段列表
      };
      
      setLedger(ledgerDetail);
    } catch (error: unknown) {
      console.error('获取台账详情失败:', error);
      message.error('获取台账详情失败');
      // 如果是认证错误，不要重复尝试获取数据
      if (error && typeof error === 'object' && 'response' in error && 
          error.response && typeof error.response === 'object' && 
          'status' in error.response && error.response.status === 401) {
        return;
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 检查权限
    if (!hasPermission(PERMISSIONS.LEDGER_VIEW)) {
      message.error('您没有权限查看此台账');
      navigate('/ledgers');
      return;
    }

    fetchLedger();
  }, [id, hasPermission, navigate]);

  const handleEdit = () => {
    navigate(`/ledgers/edit/${id}`);
  };

  const handleDelete = () => {
    // 模拟删除操作
    setLoading(true);
    setTimeout(() => {
      message.success('台账删除成功');
      navigate('/ledgers');
    }, 1000);
  };

  const handleBack = () => {
    navigate('/ledgers');
  };

  // 导出台账
  const handleExport = async (format: string) => {
    try {
      // 使用fetch API直接下载文件
      const response = await fetch(`/api/v1/ledgers/${id}/export?format=${format}`, {
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
      let filename = `台账_${id}.${format}`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=(.+)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/["']/g, '');
        }
      }
      
      // 创建Blob对象
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // 清理
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      message.success(`台账已导出为${format.toUpperCase()}格式`);
    } catch (error) {
      console.error('导出台账失败:', error);
      message.error('导出台账失败: ' + (error as Error).message);
    }
  };
  
  // 导出菜单
  const exportMenu = [
    {
      key: 'excel',
      label: 'Excel格式',
      onClick: () => handleExport('excel')
    },
    {
      key: 'csv',
      label: 'CSV格式',
      onClick: () => handleExport('csv')
    },
    {
      key: 'txt',
      label: 'TXT格式',
      onClick: () => handleExport('txt')
    }
  ];

  if (loading) {
    return <Card loading={true} />;
  }

  if (!ledger) {
    return (
      <Card>
        <Title level={4}>台账不存在</Title>
        <Button type="primary" onClick={handleBack}>返回列表</Button>
      </Card>
    );
  }

  // 将字段转换为表格数据
  const fieldColumns = [
    {
      title: '字段名称',
      dataIndex: 'name',
      key: 'name',
      width: '30%',
    },
    {
      title: '字段值',
      dataIndex: 'value',
      key: 'value',
    },
  ];

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>{ledger.title}</Title>
        </Space>
        <Space>
          <Dropdown menu={{ items: exportMenu }} placement="bottomRight">
            <Button icon={<DownloadOutlined />}>导出</Button>
          </Dropdown>
          {hasPermission(PERMISSIONS.LEDGER_EDIT) && (
            <Button 
              type="primary" 
              icon={<EditOutlined />} 
              onClick={handleEdit}
            >
              编辑
            </Button>
          )}
          {hasPermission(PERMISSIONS.LEDGER_DELETE) && (
            <Popconfirm
              title="确定要删除这个台账吗？"
              onConfirm={handleDelete}
              okText="确定"
              cancelText="取消"
            >
              <Button danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      <Descriptions bordered column={2}>
        <Descriptions.Item label="部门">{ledger.department}</Descriptions.Item>
        <Descriptions.Item label="团队">{ledger.teamName}</Descriptions.Item>
        <Descriptions.Item label="日期">{ledger.date}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={ledger.status === '已完成' ? 'success' : 'warning'}>
            {ledger.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建人">{ledger.createdBy}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{ledger.createdAt}</Descriptions.Item>
        <Descriptions.Item label="更新人">{ledger.updatedBy}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{ledger.updatedAt}</Descriptions.Item>
        <Descriptions.Item label="描述" span={2}>
          {ledger.description}
        </Descriptions.Item>
      </Descriptions>

      <Divider orientation="left">台账字段</Divider>
      <Table
        columns={fieldColumns}
        dataSource={ledger.fields}
        rowKey="id"
        pagination={false}
        bordered
      />
    </Card>
  );
};

export default LedgerDetailPage; 