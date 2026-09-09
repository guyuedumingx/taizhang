import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  message,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import {
  downloadImportFailures,
  getImportHistoryDetail,
  ImportHistoryDetail,
} from '../../api/ledgerImport';
import { LedgerService } from '../../services/LedgerService';
import { Ledger } from '../../types';
import dayjs from 'dayjs';

const { Title } = Typography;

const ImportHistoryDetailPage: React.FC = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [detail, setDetail] = useState<ImportHistoryDetail | null>(null);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!hasPermission(PERMISSIONS.LEDGER_IMPORT)) {
      message.warning('没有台账导入权限');
      navigate('/dashboard/ledgers');
      return;
    }
    if (batchId) {
      loadDetail(batchId);
    }
  }, [batchId]);

  const loadDetail = async (id: string) => {
    setLoading(true);
    try {
      const d = await getImportHistoryDetail(id);
      setDetail(d);
      // 拉批次里的台账列表
      const ledgerList: Ledger[] = [];
      for (const lid of d.created_ledger_ids || []) {
        try {
          const l = await LedgerService.getLedger(lid);
          ledgerList.push(l);
        } catch {
          // 忽略单个失败
        }
      }
      setLedgers(ledgerList);
    } catch (err: any) {
      const detailMsg = err?.response?.data?.detail;
      message.error(typeof detailMsg === 'string' ? detailMsg : '加载批次详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadFailures = async () => {
    if (!batchId) return;
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

  const ledgerColumns = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '名称', dataIndex: 'name' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const colorMap: Record<string, string> = {
          draft: 'default',
          active: 'green',
          completed: 'blue',
        };
        return <Tag color={colorMap[v] || 'default'}>{v}</Tag>;
      },
    },
    {
      title: '审批状态',
      dataIndex: 'approval_status',
      width: 100,
      render: (v: string) => {
        const colorMap: Record<string, string> = {
          pending: 'orange',
          approved: 'green',
          rejected: 'red',
        };
        return <Tag color={colorMap[v] || 'default'}>{v}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: any, record: Ledger) => (
        <Button size="small" onClick={() => navigate(`/dashboard/ledgers/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  if (!detail) {
    return (
      <div style={{ padding: 24 }}>
        <BreadcrumbNav items={[{ title: '台账管理' }, { title: '导入历史' }, { title: batchId || '' }]} />
        <Card style={{ marginTop: 16 }} loading={loading} />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <BreadcrumbNav
        items={[
          { title: '台账管理' },
          { title: '导入历史', path: '/dashboard/ledgers/import-history' },
          { title: detail.batch_id },
        ]}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <Title level={3} style={{ margin: 0 }}>批次详情</Title>
        <Space>
          {detail.failed_count > 0 && (
            <Button icon={<DownloadOutlined />} onClick={handleDownloadFailures}>
              下载失败清单
            </Button>
          )}
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard/ledgers/import-history')}>
            返回
          </Button>
        </Space>
      </div>

      <Card style={{ marginTop: 16 }}>
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="批次号">{detail.batch_id}</Descriptions.Item>
          <Descriptions.Item label="模板">{detail.template_name}</Descriptions.Item>
          <Descriptions.Item label="导入者">{detail.imported_by_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="导入时间">
            {detail.imported_at ? dayjs(detail.imported_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="文件名">{detail.filename || '-'}</Descriptions.Item>
          <Descriptions.Item label="台账数">{detail.success_count}</Descriptions.Item>
        </Descriptions>

        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Card>
              <Statistic title="成功" value={detail.success_count} valueStyle={{ color: '#3f8600' }} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="失败"
                value={detail.failed_count}
                valueStyle={{ color: detail.failed_count > 0 ? '#cf1322' : '#666' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="总行数" value={detail.total_rows} />
            </Card>
          </Col>
        </Row>
      </Card>

      <Card title="本批次台账" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          columns={ledgerColumns}
          dataSource={ledgers}
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
};

export default ImportHistoryDetailPage;
