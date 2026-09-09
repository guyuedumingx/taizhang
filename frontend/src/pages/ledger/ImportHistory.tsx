import React, { useEffect, useState } from 'react';
import { Button, Card, message, Space, Table, Tag, Typography } from 'antd';
import { DownloadOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import {
  downloadImportFailures,
  ImportHistoryItem,
  listImportHistory,
} from '../../api/ledgerImport';
import dayjs from 'dayjs';

const { Title } = Typography;

const ImportHistory: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [items, setItems] = useState<ImportHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    if (!hasPermission(PERMISSIONS.LEDGER_IMPORT)) {
      message.warning('没有台账导入权限');
      navigate('/dashboard/ledgers');
      return;
    }
    loadHistory();
  }, [page, pageSize]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const r = await listImportHistory((page - 1) * pageSize, pageSize);
      setItems(r.items || []);
      setTotal(r.total || 0);
    } catch (err) {
      message.error('加载导入历史失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadFailures = async (batchId: string) => {
    try {
      const blob = await downloadImportFailures(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `import_failures_${batchId}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      message.error('下载失败清单失败');
    }
  };

  const columns = [
    {
      title: '批次号',
      dataIndex: 'batch_id',
      render: (v: string) => <a onClick={() => navigate(`/dashboard/ledgers/import-history/${v}`)}>{v}</a>,
    },
    { title: '模板', dataIndex: 'template_name' },
    { title: '导入者', dataIndex: 'imported_by_name', render: (v: string) => v || '-' },
    {
      title: '导入时间',
      dataIndex: 'imported_at',
      render: (v: string) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    { title: '总行数', dataIndex: 'total_rows', width: 90 },
    {
      title: '成功',
      dataIndex: 'success_count',
      width: 90,
      render: (v: number) => <Tag color="green">{v}</Tag>,
    },
    {
      title: '失败',
      dataIndex: 'failed_count',
      width: 90,
      render: (v: number) => (v > 0 ? <Tag color="red">{v}</Tag> : <Tag>0</Tag>),
    },
    { title: '文件名', dataIndex: 'filename', render: (v: string) => v || '-' },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: ImportHistoryItem) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/dashboard/ledgers/import-history/${record.batch_id}`)}
          >
            详情
          </Button>
          {record.failed_count > 0 && (
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadFailures(record.batch_id)}
            >
              失败清单
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <BreadcrumbNav items={[{ title: '台账管理' }, { title: '导入历史' }]} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <Title level={3} style={{ margin: 0 }}>导入历史</Title>
        <Button icon={<ReloadOutlined />} onClick={loadHistory} loading={loading}>
          刷新
        </Button>
      </div>

      <Card style={{ marginTop: 16 }}>
        <Table
          rowKey="batch_id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default ImportHistory;
