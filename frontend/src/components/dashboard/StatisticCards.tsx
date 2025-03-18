import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import { FileTextOutlined, FormOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';

interface StatsData {
  totalLedgers: number;
  totalTemplates: number;
  totalUsers: number;
  totalTeams: number;
}

interface StatisticCardsProps {
  stats: StatsData;
  loading: boolean;
}

const StatisticCards: React.FC<StatisticCardsProps> = ({ stats, loading }) => {
  return (
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
  );
};

export default StatisticCards; 