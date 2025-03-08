import React, { useState, useEffect } from 'react';
import { Card, Typography, Descriptions, Button, Space, Tag, Divider, Table, message, Popconfirm, Dropdown, Menu } from 'antd';
import { EditOutlined, DeleteOutlined, ArrowLeftOutlined, DownloadOutlined, MoreOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';

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
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission, token } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledger, setLedger] = useState<LedgerDetail | null>(null);

  useEffect(() => {
    // 检查权限
    if (!hasPermission(PERMISSIONS.LEDGER_VIEW)) {
      message.error('您没有权限查看此台账');
      navigate('/ledgers');
      return;
    }

    // 模拟获取台账详情
    setLoading(true);
    setTimeout(() => {
      const mockData: LedgerDetail = {
        id: Number(id),
        title: `台账示例 ${id}`,
        department: '财务部',
        teamName: '财务团队',
        description: '这是一个示例台账描述，详细记录了财务部门在第一季度发现的差错问题。',
        date: '2023-05-15',
        status: '已完成',
        createdBy: '张三',
        createdAt: '2023-05-15 10:30:00',
        updatedBy: '李四',
        updatedAt: '2023-05-20 14:20:00',
        fields: [
          { id: 'field1', name: '问题类型', value: '数据错误' },
          { id: 'field2', name: '严重程度', value: '中等' },
          { id: 'field3', name: '责任人', value: '张三' },
          { id: 'field4', name: '解决方案', value: '重新核对数据并更正' },
          { id: 'field5', name: '复核人', value: '李四' },
          { id: 'field6', name: '复核结果', value: '已解决' },
        ],
      };
      
      setLedger(mockData);
      setLoading(false);
    }, 1000);
  }, [hasPermission, id, navigate]);

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
  const exportMenu = (
    <Menu
      items={[
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
      ]}
    />
  );

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
          <Dropdown overlay={exportMenu} placement="bottomRight">
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