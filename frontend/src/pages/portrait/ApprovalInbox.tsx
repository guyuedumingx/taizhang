/**
 * 数字画像-审批工作台 (P5 阶段, 批次 9)
 *
 * PRD §E1-E2: 我的待审批 + approve / reject / transfer 操作
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有操作走 api
 * 集成指南 §5 雷区 12 (Rule 12): reject 必须填 comment, 失败显性化
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
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

const TYPE_LABEL: Record<string, string> = {
  special_work: '专项工作',
  profile_edit: '档案修改',
  skill_tag_edit: '亮点标签',
};

const ApprovalInbox: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<PortraitAPI.SubmissionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [acting, setActing] = useState(false);
  const [rejectForm] = Form.useForm();
  const [transferForm] = Form.useForm();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await PortraitAPI.listMyPendingApprovals({
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
    try {
      const data = await PortraitAPI.getSubmissionDetail(id);
      Modal.info({
        title: `${TYPE_LABEL[data.submission_type]} #${data.id}`,
        width: 640,
        icon: null,
        okText: '关闭',
        content: (
          <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
            {JSON.stringify(
              typeof data.payload === 'string' ? safeJSON(data.payload) : data.payload,
              null,
              2
            )}
          </pre>
        ),
      });
    } catch (err: any) {
      message.error(`详情加载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleApprove = async (id: number) => {
    setActing(true);
    try {
      await PortraitAPI.approveSubmission(id, '已审');
      message.success('已通过');
      await fetchList();
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
      return;  // 表单校验失败
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
      await fetchList();
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
      await fetchList();
    } catch (err: any) {
      message.error(`转交失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setActing(false);
    }
  };

  return (
    <div>
      <BreadcrumbNav items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '待审批' }]} />
      <Card
        title={<Title level={4} style={{ margin: 0 }}>待审批</Title>}
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
              title: '提交人',
              dataIndex: 'submitter_name',
              render: (v: string, row: PortraitAPI.SubmissionRecord) => (
                <Space direction="vertical" size={0}>
                  <Text>{v}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    EHR {row.submitter_ehr_id}
                  </Text>
                </Space>
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
                <Space wrap>
                  <Button
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => openDetail(row.id)}
                  >
                    详情
                  </Button>
                  <Popconfirm
                    title="确认通过?"
                    onConfirm={() => handleApprove(row.id)}
                    okButtonProps={{ loading: acting }}
                  >
                    <Button
                      size="small"
                      type="primary"
                      icon={<CheckOutlined />}
                      loading={acting}
                    >
                      通过
                    </Button>
                  </Popconfirm>
                  <Button
                    size="small"
                    danger
                    icon={<CloseOutlined />}
                    onClick={() => openReject(row.id)}
                  >
                    驳回
                  </Button>
                  <Button
                    size="small"
                    icon={<SwapOutlined />}
                    onClick={() => openTransfer(row.id)}
                  >
                    转交
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 驳回 Modal (强制填 comment) */}
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
            <Input.TextArea rows={4} placeholder="说明驳回原因..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 转交 Modal (transferred_to_id 必填) */}
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
            <Input.TextArea rows={3} placeholder="转交说明..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

function safeJSON(s: string): unknown {
  try { return JSON.parse(s); } catch { return s; }
}

export default ApprovalInbox;