/**
 * 数字画像-我的提交 (P5 阶段, 批次 9)
 *
 * PRD §B3-B4: 我的提交列表 + 详情 (含审批流)
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有更新走 api
 * P5 MVP 不含 B1 创建表单 (用户决定), 仅展示 + 撤回
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Modal,
  Descriptions,
  Timeline,
  Space,
  Typography,
  Popconfirm,
  message,
  Spin,
} from 'antd';
import { ReloadOutlined, EyeOutlined, RollbackOutlined } from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text, Paragraph } = Typography;

const TYPE_LABEL: Record<string, string> = {
  special_work: '专项工作',
  profile_edit: '档案修改',
  skill_tag_edit: '亮点标签',
};

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  pending: 'processing',
  approved: 'success',
  rejected: 'error',
  cancelled: 'default',
};

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  pending: '审批中',
  approved: '已通过',
  rejected: '已驳回',
  cancelled: '已撤回',
};

const ACTION_LABEL: Record<string, string> = {
  submit: '提交',
  approve: '通过',
  reject: '驳回',
  transfer: '转交',
  withdraw: '撤回',
};

const MySubmissions: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<PortraitAPI.SubmissionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await PortraitAPI.listMySubmissions({
        skip: (page - 1) * size,
        limit: size,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err: any) {
      message.error(`加载失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
  }, [page, size]);

  const openDetail = async (id: number) => {
    setDetailLoading(true);
    Modal.info({
      title: '加载中...',
      content: <Spin />,
      okButtonProps: { style: { display: 'none' } },
      maskClosable: true,
    });
    try {
      const data = await PortraitAPI.getSubmissionDetail(id);
      Modal.destroyAll();
      Modal.info({
        title: `提交 #${data.id} - ${TYPE_LABEL[data.submission_type]}`,
        width: 720,
        icon: null,
        okText: '关闭',
        content: <DetailContent detail={data} />,
      });
    } catch (err: any) {
      Modal.destroyAll();
      message.error(`详情加载失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCancel = async (id: number) => {
    setSubmitting(true);
    try {
      await PortraitAPI.cancelSubmission(id);
      message.success('已撤回');
      await fetchList();
    } catch (err: any) {
      message.error(`撤回失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <BreadcrumbNav items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '我的提交' }]} />
      <Card
        title={<Title level={4} style={{ margin: 0 }}>我的提交</Title>}
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchList} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            onChange: (p, s) => { setPage(p); setSize(s); },
          }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            {
              title: '类型',
              dataIndex: 'submission_type',
              render: (v: string) => <Tag>{TYPE_LABEL[v] || v}</Tag>,
            },
            {
              title: '状态',
              dataIndex: 'status',
              render: (v: string) => (
                <Tag color={STATUS_COLOR[v]}>{STATUS_LABEL[v] || v}</Tag>
              ),
            },
            {
              title: '提交时间',
              dataIndex: 'submitted_at',
              render: (v?: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
            },
            {
              title: '操作',
              key: 'action',
              render: (_, row: PortraitAPI.SubmissionRecord) => (
                <Space>
                  <Button
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => openDetail(row.id)}
                    loading={detailLoading}
                  >
                    详情
                  </Button>
                  {row.status === 'pending' && (
                    <Popconfirm
                      title="确认撤回该提交?"
                      onConfirm={() => handleCancel(row.id)}
                      okButtonProps={{ loading: submitting }}
                    >
                      <Button
                        size="small"
                        danger
                        icon={<RollbackOutlined />}
                        loading={submitting}
                      >
                        撤回
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

// 详情内容 (在 Modal.info 内渲染)
const DetailContent: React.FC<{ detail: PortraitAPI.SubmissionDetail }> = ({ detail }) => {
  let payload: any = detail.payload;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch { /* 保留原值 */ }
  }
  return (
    <div>
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
        <Descriptions.Item label="类型">
          <Tag>{TYPE_LABEL[detail.submission_type]}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={STATUS_COLOR[detail.status]}>{STATUS_LABEL[detail.status]}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="提交人">
          {detail.submitter_name} (EHR {detail.submitter_ehr_id})
        </Descriptions.Item>
        <Descriptions.Item label="提交时间">
          {detail.submitted_at ? new Date(detail.submitted_at).toLocaleString('zh-CN') : '-'}
        </Descriptions.Item>
        {detail.completed_at && (
          <Descriptions.Item label="完成时间">
            {new Date(detail.completed_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
        )}
      </Descriptions>
      <Title level={5} style={{ marginTop: 16 }}>业务数据</Title>
      <Paragraph>
        <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
          {JSON.stringify(payload, null, 2)}
        </pre>
      </Paragraph>
      <Title level={5}>审批流</Title>
      {detail.approvals.length === 0 ? (
        <Text type="secondary">无审批记录</Text>
      ) : (
        <Timeline
          items={detail.approvals.map(a => ({
            color:
              a.action === 'approve' ? 'green' :
              a.action === 'reject' ? 'red' :
              a.action === 'transfer' ? 'blue' :
              a.action === 'withdraw' ? 'gray' : 'gray',
            children: (
              <>
                <Text strong>{ACTION_LABEL[a.action] || a.action}</Text>
                {' '}by {a.approver_name || `#${a.approver_id}`}
                {' '}<Text type="secondary">{new Date(a.created_at).toLocaleString('zh-CN')}</Text>
                {a.comment && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">意见: </Text>
                    {a.comment}
                  </div>
                )}
                {a.transferred_to_id && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">转交给: </Text>
                    #{a.transferred_to_id}
                  </div>
                )}
              </>
            ),
          }))}
        />
      )}
    </div>
  );
};

export default MySubmissions;