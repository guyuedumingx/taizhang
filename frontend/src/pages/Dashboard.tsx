import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Button, Typography, Divider } from 'antd';
import { FileTextOutlined, FormOutlined, TeamOutlined, UserOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { PERMISSIONS } from '../config';

const { Title } = Typography;

interface LedgerItem {
  id: number;
  title: string;
  department: string;
  createdBy: string;
  createdAt: string;
  status: string;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalLedgers: 0,
    totalTemplates: 0,
    totalUsers: 0,
    totalTeams: 0,
  });
  const [recentLedgers, setRecentLedgers] = useState<LedgerItem[]>([]);

  useEffect(() => {
    // 模拟获取数据
    setTimeout(() => {
      setStats({
        totalLedgers: 156,
        totalTemplates: 12,
        totalUsers: 45,
        totalTeams: 8,
      });
      
      setRecentLedgers([
        {
          id: 1,
          title: '2023年第一季度财务差错',
          department: '财务部',
          createdBy: '张三',
          createdAt: '2023-04-01',
          status: '已完成',
        },
        {
          id: 2,
          title: '2023年5月生产质量问题',
          department: '生产部',
          createdBy: '李四',
          createdAt: '2023-06-02',
          status: '处理中',
        },
        {
          id: 3,
          title: '2023年上半年客户投诉',
          department: '客服部',
          createdBy: '王五',
          createdAt: '2023-07-15',
          status: '已完成',
        },
        {
          id: 4,
          title: '2023年7月设备故障记录',
          department: '设备部',
          createdBy: '赵六',
          createdAt: '2023-08-01',
          status: '处理中',
        },
      ]);
      
      setLoading(false);
    }, 1000);
  }, []);

  const columns = [
    {
      title: '台账标题',
      dataIndex: 'title',
      key: 'title',
      width: '30%',
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '创建人',
      dataIndex: 'createdBy',
      key: 'createdBy',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text: string) => (
        <span style={{ color: text === '已完成' ? '#52c41a' : '#faad14' }}>
          {text}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: LedgerItem) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />}
          onClick={() => navigate(`/ledgers/${record.id}`)}
          disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div className="container">
      <div className="page-header">
        <Title level={3} className="page-title">系统概览</Title>
        <div>
          <Button type="primary" onClick={() => navigate('/ledgers/new')} disabled={!hasPermission(PERMISSIONS.LEDGER_CREATE)}>
            创建台账
          </Button>
        </div>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card" hoverable>
            <Statistic
              className="dashboard-statistic"
              title="台账总数"
              value={stats.totalLedgers}
              prefix={<FileTextOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card" hoverable>
            <Statistic
              className="dashboard-statistic"
              title="模板总数"
              value={stats.totalTemplates}
              prefix={<FormOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card" hoverable>
            <Statistic
              className="dashboard-statistic"
              title="用户总数"
              value={stats.totalUsers}
              prefix={<UserOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card" hoverable>
            <Statistic
              className="dashboard-statistic"
              title="团队总数"
              value={stats.totalTeams}
              prefix={<TeamOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      <div className="page-header">
        <Title level={4} className="page-title">最近台账</Title>
        <Button type="link" onClick={() => navigate('/ledgers')}>
          查看全部
        </Button>
      </div>

      <Card className="dashboard-card">
        <Table
          columns={columns}
          dataSource={recentLedgers}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default Dashboard; 