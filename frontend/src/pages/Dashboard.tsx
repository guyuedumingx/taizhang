import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Button, Typography, Divider, message, Tooltip, Empty } from 'antd';
import { FileTextOutlined, FormOutlined, TeamOutlined, UserOutlined, EyeOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { PERMISSIONS } from '../config';
import { LedgerService } from '../services/LedgerService';
import { TemplateService } from '../services/TemplateService';
import { TeamService } from '../services/TeamService';
import { UserService } from '../services/UserService';
import { Ledger, Template } from '../types';

const { Title, Paragraph } = Typography;

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
  const [recentLedgers, setRecentLedgers] = useState<Ledger[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        // 获取台账总数
        const ledgers = await LedgerService.getLedgers();
        
        // 获取模板总数
        const templates = await TemplateService.getTemplates();
        setTemplates(templates);
        
        // 获取用户总数
        const users = await UserService.getUsers();
        
        // 获取团队总数
        const teams = await TeamService.getTeams();
        
        // 更新统计数据
        setStats({
          totalLedgers: ledgers.length,
          totalTemplates: templates.length,
          totalUsers: users.length,
          totalTeams: teams.length,
        });
        
        // 更新最近台账数据（取最新的4个）
        const sortedLedgers = [...ledgers].sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ).slice(0, 4);
        
        setRecentLedgers(sortedLedgers);
      } catch (error) {
        console.error('获取仪表盘数据失败:', error);
        message.error('获取仪表盘数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  // 直接导航到创建台账页面并使用选定的模板
  const navigateToCreateLedger = (templateId: number) => {
    navigate(`/dashboard/ledgers/new?template_id=${templateId}`);
  };

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
      render: (text: string) => (
        <span style={{ color: text === '已完成' ? '#52c41a' : '#faad14' }}>
          {text}
        </span>
      ),
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
    <div className="container">
      <div className="page-header">
        <Title level={3} className="page-title">系统概览</Title>
        <div>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => navigate('/dashboard/ledgers/new')} 
            disabled={!hasPermission(PERMISSIONS.LEDGER_CREATE)}
          >
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

      {hasPermission(PERMISSIONS.LEDGER_CREATE) && (
        <>
          <Divider />
          
          <div className="page-header">
            <Title level={4} className="page-title">
              快速登记台账
            </Title>
            <Button 
              type="link" 
              onClick={() => navigate('/dashboard/templates')}
            >
              管理模板
            </Button>
          </div>
          
          <Paragraph style={{ marginBottom: 16 }}>
            选择模板类型，快速创建对应台账
          </Paragraph>
          
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            {loading ? (
              <Col span={24}>
                <Card loading={true} />
              </Col>
            ) : templates.length > 0 ? (
              templates.slice(0, 8).map(template => (
                <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
                  <Card 
                    hoverable 
                    className="template-card"
                    onClick={() => navigateToCreateLedger(template.id)}
                    style={{ height: '100%' }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                      <div style={{ flex: '1 0 auto' }}>
                        <div style={{ fontSize: 36, color: '#1890ff', textAlign: 'center', marginBottom: 12 }}>
                          <FormOutlined />
                        </div>
                        <Tooltip title={template.name}>
                          <Title level={5} ellipsis={{ rows: 1 }} style={{ textAlign: 'center' }}>
                            {template.name}
                          </Title>
                        </Tooltip>
                      </div>
                      <Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0, fontSize: 12 }}>
                        {template.description || '无描述'}
                      </Paragraph>
                      <div style={{ marginTop: 12, textAlign: 'center' }}>
                        <Button type="primary" size="small">
                          创建台账
                        </Button>
                      </div>
                    </div>
                  </Card>
                </Col>
              ))
            ) : (
              <Col span={24}>
                <Empty description="暂无模板，请先创建模板" />
              </Col>
            )}
            {templates.length > 8 && (
              <Col span={24} style={{ textAlign: 'center', marginTop: 8 }}>
                <Button type="link" onClick={() => navigate('/dashboard/templates')}>
                  查看更多模板
                </Button>
              </Col>
            )}
          </Row>
        </>
      )}

      <Divider />

      <div className="page-header">
        <Title level={4} className="page-title">最近台账</Title>
        <Button type="link" onClick={() => navigate('/dashboard/ledgers')}>
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