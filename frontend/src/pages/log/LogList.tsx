import React, { useState, useEffect } from 'react';
import { Card, Tabs, message, TablePaginationConfig } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { SystemLog, AuditLog, LogQueryParams } from '../../types';
import { LogService } from '../../services/LogService';
import SystemLogTable from '../../components/log/SystemLogTable';
import AuditLogTable from '../../components/log/AuditLogTable';
import LogSearchForm from '../../components/log/LogSearchForm';

const { TabPane } = Tabs;

interface FormValues extends LogQueryParams {
  date_range?: [any, any];
}

const LogList: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [activeTab, setActiveTab] = useState<string>('system');
  const [systemLoading, setSystemLoading] = useState<boolean>(false);
  const [auditLoading, setAuditLoading] = useState<boolean>(false);
  const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [systemTotal, setSystemTotal] = useState<number>(0);
  const [auditTotal, setAuditTotal] = useState<number>(0);
  const [systemParams, setSystemParams] = useState<LogQueryParams>({
    page: 1,
    page_size: 10,
  });
  const [auditParams, setAuditParams] = useState<LogQueryParams>({
    page: 1,
    page_size: 10,
  });

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.LOG_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    // 加载初始数据
    fetchSystemLogs(systemParams);
    fetchAuditLogs(auditParams);
  }, [hasPermission]);

  // 获取系统日志
  const fetchSystemLogs = async (params: LogQueryParams) => {
    setSystemLoading(true);
    try {
      const response = await LogService.getSystemLogs(params);
      setSystemLogs(response.items);
      setSystemTotal(response.total);
    } catch (error) {
      console.error('获取系统日志失败:', error);
      message.error('获取系统日志失败');
    } finally {
      setSystemLoading(false);
    }
  };

  // 获取审计日志
  const fetchAuditLogs = async (params: LogQueryParams) => {
    setAuditLoading(true);
    try {
      const response = await LogService.getAuditLogs(params);
      setAuditLogs(response.items);
      setAuditTotal(response.total);
    } catch (error) {
      console.error('获取审计日志失败:', error);
      message.error('获取审计日志失败');
    } finally {
      setAuditLoading(false);
    }
  };

  // 处理标签页切换
  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };

  // 处理系统日志分页变化
  const handleSystemTableChange = (pagination: TablePaginationConfig) => {
    const params = {
      ...systemParams,
      page: pagination.current || 1,
      page_size: pagination.pageSize || 10,
    };
    setSystemParams(params);
    fetchSystemLogs(params);
  };

  // 处理审计日志分页变化
  const handleAuditTableChange = (pagination: TablePaginationConfig) => {
    const params = {
      ...auditParams,
      page: pagination.current || 1,
      page_size: pagination.pageSize || 10,
    };
    setAuditParams(params);
    fetchAuditLogs(params);
  };

  // 处理系统日志搜索
  const handleSystemSearch = (values: FormValues) => {
    // 处理日期范围
    let params = { ...values } as LogQueryParams;
    if (values.date_range && values.date_range.length === 2) {
      const [startDate, endDate] = values.date_range;
      if (startDate && startDate.format) {
        params.start_date = startDate.format('YYYY-MM-DD HH:mm:ss');
      }
      if (endDate && endDate.format) {
        params.end_date = endDate.format('YYYY-MM-DD HH:mm:ss');
      }
      delete params.date_range;
    }

    // 重置分页并添加分页参数
    params = {
      ...params,
      page: 1,
      page_size: systemParams.page_size,
    };

    setSystemParams(params);
    fetchSystemLogs(params);
  };

  // 处理审计日志搜索
  const handleAuditSearch = (values: FormValues) => {
    // 处理日期范围
    let params = { ...values } as LogQueryParams;
    if (values.date_range && values.date_range.length === 2) {
      const [startDate, endDate] = values.date_range;
      if (startDate && startDate.format) {
        params.start_date = startDate.format('YYYY-MM-DD HH:mm:ss');
      }
      if (endDate && endDate.format) {
        params.end_date = endDate.format('YYYY-MM-DD HH:mm:ss');
      }
      delete params.date_range;
    }

    // 重置分页并添加分页参数
    params = {
      ...params,
      page: 1,
      page_size: auditParams.page_size,
    };

    setAuditParams(params);
    fetchAuditLogs(params);
  };

  // 重置系统日志搜索
  const handleSystemReset = () => {
    const params = {
      page: 1,
      page_size: systemParams.page_size,
    };
    setSystemParams(params);
    fetchSystemLogs(params);
  };

  // 重置审计日志搜索
  const handleAuditReset = () => {
    const params = {
      page: 1,
      page_size: auditParams.page_size,
    };
    setAuditParams(params);
    fetchAuditLogs(params);
  };

  return (
    <Card title="系统日志" bordered={false}>
      <Tabs activeKey={activeTab} onChange={handleTabChange}>
        <TabPane tab="系统日志" key="system">
          <LogSearchForm
            type="system"
            onSearch={handleSystemSearch}
            onReset={handleSystemReset}
            loading={systemLoading}
          />
          <SystemLogTable
            logs={systemLogs}
            loading={systemLoading}
            pagination={{
              current: systemParams.page || 1,
              pageSize: systemParams.page_size || 10,
              total: systemTotal,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total: number) => `共 ${total} 条记录`,
            }}
            onChange={handleSystemTableChange}
          />
        </TabPane>
        <TabPane tab="审计日志" key="audit">
          <LogSearchForm
            type="audit"
            onSearch={handleAuditSearch}
            onReset={handleAuditReset}
            loading={auditLoading}
          />
          <AuditLogTable
            logs={auditLogs}
            loading={auditLoading}
            pagination={{
              current: auditParams.page || 1,
              pageSize: auditParams.page_size || 10,
              total: auditTotal,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total: number) => `共 ${total} 条记录`,
            }}
            onChange={handleAuditTableChange}
          />
        </TabPane>
      </Tabs>
    </Card>
  );
};

export default LogList; 