/**
 * 数字画像-审批工作台 (P7 阶段, 批次 13) F1 聚合页
 *
 * PRD §E1-E3:
 *   - Tab 1: 待审批 (current_approver_id == me)
 *   - Tab 2: 我审批过的历史 (ApproverRecord.approver_id == me, 去重, completed_at desc)
 *
 * 操作 (仅 Tab 1 可用):
 *   - 通过 / 驳回 (必填意见) / 转交
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有操作走 api
 * 集成指南 §5 雷区 12 (Rule 12): reject 必须填 comment, 失败显性化
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Space,
  Typography,
  message,
  Popconfirm,
} from 'antd';
import {
  ReloadOutlined,
  CheckOutlined,
  CloseOutlined,
  SwapOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;
const { TextArea } = Input;

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

// ============================================================================
// 详情内容 (复用, 在 Modal.info 内渲染)
// ============================================================================
const DetailContent: React.FC<{ detail: PortraitAPI.SubmissionDetail }> = ({ detail }) => {
  let payload: any = detail.payload;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch { /* 保留原值 */ }
  }
  return (
    <div>
      <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
        {JSON.stringify(payload, null, 2)}
      </pre>
      {detail.approvals.length > 0 && (
        <>
          <Title level={5} style={{ marginTop: 16 }}>审批流</Title>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            {detail.approvals.map((a) => (
              <div key={a.id}>
                <Text>
                  [{new Date(a.created_at).toLocaleString('zh-CN')}]
                  {' '}<Text strong>{a.action}</Text>
                  {' '}by {a.approver_name || `#${a.approver_id}`}
                </Text>
                {a.comment && <div><Text type="secondary">评论: </Text>{a.comment}</div>}
                {a.transferred_to_id && <div><Text type="secondary">转交给: </Text>#{a.transferred_to_id}</div>}
              </div>
            ))}
          </Space>
        </>
      )}
    </div>
  );
};

// ============================================================================
// 共享: 详情 + 通过/驳回/转交 操作列 (Tab 1: 待审批)
// ============================================================================
interface ActionColumnsProps {
  acting: boolean;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onTransfer: (id: number) => void;
  onDetail: (id: number) => void;
}

const ACTION_COLUMNS = (props: ActionColumnsProps) => [
  {
    title: '操作',
    key: 'action',
    render: (_: unknown, row: PortraitAPI.SubmissionRecord) => (
      <Space wrap>
        <Button size="small" icon={<EyeOutlined />} onClick={() => props.onDetail(row.id)}>
          详情
        </Button>
        <Popconfirm
          title="确认通过?"
          onConfirm={() => props.onApprove(row.id)}
          okButtonProps={{ loading: props.acting }}
        >
          <Button size="small" type="primary" icon={<CheckOutlined />} loading={props.acting}>
            通过
          </Button>
        </Popconfirm>
        <Button size="small" danger icon={<CloseOutlined />} onClick={() => props.onReject(row.id)}>
          驳回
        </Button>
        <Button size="small" icon={<SwapOutlined />} onClick={() => props.onTransfer(row.id)}>
          转交
        </Button>
      </Space>
    ),
  },
];

// ============================================================================
// 主页面 (F1 聚合)
// ============================================================================
const ApprovalInbox: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  // Tab 1 state
  const [pendingLoading, setPendingLoading] = useState(true);
  const [pendingItems, setPendingItems] = useState<PortraitAPI.SubmissionRecord[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingSize, setPendingSize] = useState(20);

  // Tab 2 state
  const [historyLoading, setHistoryLoading] = useState(false);  // 懒加载
  const [historyItems, setHistoryItems] = useState<PortraitAPI.SubmissionRecord[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historySize, setHistorySize] = useState(20);

  // 共享操作 state
  const [acting, setActing] = useState(false);
  const [rejectForm] = Form.useForm();
  const [transferForm] = Form.useForm();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);

  // ----- 待审批 fetch -----
  const fetchPending = async () => {
    setPendingLoading(true);
    try {
      const data = await PortraitAPI.listMyPendingApprovals({
        skip: (pendingPage - 1) * pendingSize,
        limit: pendingSize,
      });
      setPendingItems(data.items);
      setPendingTotal(data.total);
    } catch (err: any) {
      message.error(`加载待审批失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setPendingLoading(false);
    }
  };

  // ----- 历史 fetch -----
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await PortraitAPI.listMyApprovalHistory({
        skip: (historyPage - 1) * historySize,
        limit: historySize,
      });
      setHistoryItems(data.items);
      setHistoryTotal(data.total);
    } catch (err: any) {
      message.error(`加载历史失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setHistoryLoading(false);
    }
  };

  // 首次挂载 + Tab 1 分页变化 → 拉待审批
  useEffect(() => {
    fetchPending();
  }, [pendingPage, pendingSize]);

  // 切到 Tab 2 首次拉历史, 已拉过则按分页拉
  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, historyPage, historySize]);

  // ----- 详情 -----
  const openDetail = async (id: number) => {
    try {
      const data = await PortraitAPI.getSubmissionDetail(id);
      Modal.info({
        title: `${TYPE_LABEL[data.submission_type]} #${data.id} - ${STATUS_LABEL[data.status]}`,
        width: 720,
        icon: null,
        okText: '关闭',
        content: <DetailContent detail={data} />,
      });
    } catch (err: any) {
      message.error(`详情加载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  // ----- 操作 (仅影响待审批) -----
  const handleApprove = async (id: number) => {
    setActing(true);
    try {
      await PortraitAPI.approveSubmission(id, '已审');
      message.success('已通过');
      await fetchPending();
    } catch (err: any) {
      message.error(`通过失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActing(false);
    }
  };

  const openReject = (id: number) => {
    setActiveId(id);
    rejectForm.resetFields();
    setRejectOpen(true);
  };

  const submitReject = async () => {
    if (!activeId) return;
    let values: { comment: string };
    try {
      values = await rejectForm.validateFields();
    } catch {
      return;
    }
    if (!values.comment || !values.comment.trim()) {
      message.error('驳回必须填写意见');
      return;
    }
    setActing(true);
    try {
      await PortraitAPI.rejectSubmission(activeId, values.comment.trim());
      message.success('已驳回');
      setRejectOpen(false);
      await fetchPending();
    } catch (err: any) {
      message.error(`驳回失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActing(false);
    }
  };

  const openTransfer = (id: number) => {
    setActiveId(id);
    transferForm.resetFields();
    setTransferOpen(true);
  };

  const submitTransfer = async () => {
    if (!activeId) return;
    let values: { transferred_to_id: number; comment?: string };
    try {
      values = await transferForm.validateFields();
    } catch {
      return;
    }
    setActing(true);
    try {
      await PortraitAPI.transferSubmission(activeId, values.transferred_to_id, values.comment);
      message.success(`已转交给用户 #${values.transferred_to_id}`);
      setTransferOpen(false);
      await fetchPending();
    } catch (err: any) {
      message.error(`转交失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActing(false);
    }
  };

  // ----- 列定义 -----
  const baseColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '类型',
      dataIndex: 'submission_type',
      render: (v: string) => <Tag>{TYPE_LABEL[v] || v}</Tag>,
    },
    {
      title: '提交人',
      dataIndex: 'submitter_name',
      render: (v: string, row: PortraitAPI.SubmissionRecord) => (
        <Space direction="vertical" size={0}>
          <Text>{v}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>EHR {row.submitter_ehr_id}</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (v: string) => <Tag color={STATUS_COLOR[v]}>{STATUS_LABEL[v] || v}</Tag>,
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      render: (v?: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      render: (v?: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
  ];

  const actionProps: ActionColumnsProps = {
    acting,
    onApprove: handleApprove,
    onReject: openReject,
    onTransfer: openTransfer,
    onDetail: openDetail,
  };

  const pendingColumns = [...baseColumns, ...ACTION_COLUMNS(actionProps)];

  // 历史 tab 只看详情, 无操作列
  const historyColumns = [
    ...baseColumns,
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, row: PortraitAPI.SubmissionRecord) => (
        <Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(row.id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <BreadcrumbNav items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '审批工作台' }]} />
      <Card
        title={<Title level={4} style={{ margin: 0 }}>审批工作台</Title>}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={activeTab === 'pending' ? fetchPending : fetchHistory}
              loading={activeTab === 'pending' ? pendingLoading : historyLoading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as 'pending' | 'history')}
          items={[
            {
              key: 'pending',
              label: `待审批 (${pendingTotal})`,
              children: (
                <Table
                  rowKey="id"
                  loading={pendingLoading}
                  dataSource={pendingItems}
                  pagination={{
                    current: pendingPage,
                    pageSize: pendingSize,
                    total: pendingTotal,
                    showSizeChanger: true,
                    onChange: (p, s) => { setPendingPage(p); setPendingSize(s); },
                  }}
                  columns={pendingColumns}
                />
              ),
            },
            {
              key: 'history',
              label: `历史 (${historyTotal})`,
              children: (
                <Table
                  rowKey="id"
                  loading={historyLoading}
                  dataSource={historyItems}
                  pagination={{
                    current: historyPage,
                    pageSize: historySize,
                    total: historyTotal,
                    showSizeChanger: true,
                    onChange: (p, s) => { setHistoryPage(p); setHistorySize(s); },
                  }}
                  columns={historyColumns}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 驳回 Modal */}
      <Modal
        title="驳回提交"
        open={rejectOpen}
        onOk={submitReject}
        onCancel={() => setRejectOpen(false)}
        confirmLoading={acting}
        okText="确认驳回"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <Form form={rejectForm} layout="vertical">
          <Form.Item
            label="驳回意见 (必填)"
            name="comment"
            rules={[
              { required: true, message: '驳回必须填写意见' },
              { whitespace: true, message: '意见不能全是空白' },
              { min: 2, message: '意见至少 2 个字符' },
            ]}
          >
            <TextArea rows={4} placeholder="说明驳回原因..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 转交 Modal */}
      <Modal
        title="转交提交"
        open={transferOpen}
        onOk={submitTransfer}
        onCancel={() => setTransferOpen(false)}
        confirmLoading={acting}
        okText="确认转交"
        cancelText="取消"
      >
        <Form form={transferForm} layout="vertical">
          <Form.Item
            label="转交给 (用户 ID)"
            name="transferred_to_id"
            rules={[{ required: true, message: '必须指定转交目标用户 ID' }]}
          >
            <Input type="number" placeholder="输入目标用户 ID" />
          </Form.Item>
          <Form.Item label="备注 (选填)" name="comment">
            <TextArea rows={3} placeholder="转交说明..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApprovalInbox;