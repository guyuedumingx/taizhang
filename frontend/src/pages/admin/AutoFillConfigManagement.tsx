import React, { useState, useEffect } from 'react';
import { Table, Button, Card, Typography, message, Tag, Space } from 'antd';
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { api } from '../../api/index';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

interface TriggerConfig {
  field_name: string;
  api_url: string;
  headers?: Record<string, string>;
  timeout?: number;
  retry_times?: number;
  enabled: boolean;
  description?: string;
}

const AutoFillConfigManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<TriggerConfig[]>([]);

  const canEdit = hasPermission(PERMISSIONS.TEMPLATE_EDIT);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/auto-fill-configs/');
      setConfigs(res.data);
    } catch {
      message.error('获取配置列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleReload = async () => {
    try {
      const res = await api.post('/auto-fill-configs/reload');
      message.success(res.data.message);
      fetchData();
    } catch {
      message.error('重载失败');
    }
  };

  const columns: ColumnsType<TriggerConfig> = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 150,
      render: (v: string, r: TriggerConfig) => (
        <Space>
          <span>{v}</span>
          {r.enabled ? <Tag color="green">启用</Tag> : <Tag color="default">禁用</Tag>}
        </Space>
      ),
    },
    {
      title: 'API 地址',
      dataIndex: 'api_url',
      key: 'api_url',
      ellipsis: true,
    },
    {
      title: '请求头',
      dataIndex: 'headers',
      key: 'headers',
      width: 150,
      ellipsis: true,
      render: (v: Record<string, string>) =>
        v && Object.keys(v).length > 0 ? JSON.stringify(v) : <Tag>无</Tag>,
    },
    {
      title: '超时(秒)',
      dataIndex: 'timeout',
      key: 'timeout',
      width: 80,
    },
    {
      title: '重试',
      dataIndex: 'retry_times',
      key: 'retry_times',
      width: 60,
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  return (
    <>
      <BreadcrumbNav
        items={[{ title: '系统管理' }, { title: '自动填充配置' }]}
        showBackButton={false}
      />
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space align="center">
            <ThunderboltOutlined style={{ fontSize: 20, color: '#D05A6E' }} />
            <Title level={4} style={{ margin: 0 }}>自动填充配置</Title>
          </Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReload}
            disabled={!canEdit}
          >
            热重载配置
          </Button>
        </div>

        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          配置文件路径：<Text code>backend/auto_fill_triggers.json</Text>
          ，修改后点击「热重载配置」或重启服务生效。
        </Text>

        <Table
          columns={columns}
          dataSource={configs}
          rowKey="field_name"
          loading={loading}
          pagination={false}
        />
      </Card>
    </>
  );
};

export default AutoFillConfigManagement;
