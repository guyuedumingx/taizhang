import React, { useState, useEffect } from 'react';
import { Button, Typography, Divider, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { PERMISSIONS } from '../config';
import { LedgerService } from '../services/LedgerService';
import { TemplateService } from '../services/TemplateService';
import { TeamService } from '../services/TeamService';
import { UserService } from '../services/UserService';
import { Ledger, Template } from '../types';
import { 
  StatisticCards, 
  QuickRegistrationTemplates, 
  RecentLedgersTable 
} from '../components/dashboard';
import api from '../api';

const { Title } = Typography;

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
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const overviewData = await api.statistics.overview();
      console.log('获取到概览数据:', overviewData);
      setTemplates(overviewData.templates);
      setRecentLedgers(overviewData.ledgers);
      
      // 更新统计数据
      setStats({
        totalLedgers: overviewData.ledgers.length,
        totalTemplates: overviewData.templates.length,
        totalUsers: overviewData.users_count,
        totalTeams: overviewData.teams_count,
      });
      
      // 更新最近台账数据（取最新的4个）
      const sortedLedgers = [...overviewData.ledgers].sort((a, b) => 
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

  // 直接导航到创建台账页面并使用选定的模板
  const navigateToCreateLedger = (templateId: number) => {
    navigate(`/dashboard/ledgers/new?template_id=${templateId}`);
  };

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

      <StatisticCards stats={stats} loading={loading} />

      {hasPermission(PERMISSIONS.LEDGER_CREATE) && (
        <>
          <Divider />
          <QuickRegistrationTemplates 
            templates={templates} 
            loading={loading} 
            onTemplateSelect={navigateToCreateLedger} 
          />
        </>
      )}

      <Divider />
      
      <RecentLedgersTable ledgers={recentLedgers} loading={loading} />
    </div>
  );
};

export default Dashboard; 