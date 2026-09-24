/**
 * 数字画像-家访 (P6 阶段, 批次 11)
 *
 * PRD §C §9.1: 家访审批流 (4 类审批共用审批工作台模式)
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有更新走 api
 * 集成指南 §5 雷区 12: reject 必须填 comment, 显式 400
 *
 * MVP 范围:
 *  - 列表 (status/visit_year/visited_ehr_id 筛选)
 *  - 详情查看 (含 22 个字段)
 *  - 审批操作: 通过 (admin/current_approver) / 驳回 (admin/current_approver, 必须 comment) / 撤回 (仅 visitor, 仅 pending)
 *  - 草稿提交 (仅 visitor)
 *
 * 暂不做 (P7+):
 *  - 创建家访草稿表单 (用 P6 后端已有 POST 端点, 前端表单留待 P7)
 *  - PDF 导出 (P5 之前在 digital_portrait 仓有, 待集成)
 */
import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Modal,
  Descriptions,
  Space,
  Typography,
  Popconfirm,
  Input,
  Form,
  message,
  Spin,
  Tabs,
} from 'antd';
import {
  ReloadOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  RollbackOutlined,
  SendOutlined,
} from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title, Text } = Typography;

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

const HomeVisits: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<PortraitAPI.HomeVisitItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<PortraitAPI.HomeVisitDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectForm] = Form.useForm();
  const [rejectingId, setRejectingId] = useState<number | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await PortraitAPI.listHomeVisits({
        status: statusFilter,
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, size, statusFilter]);

  const openDetail = async (id: number) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const data = await PortraitAPI.getHomeVisit(id);
      setDetail(data);
    } catch (err: any) {
      message.error(`加载详情失败: ${err?.response?.data?.detail || err.message}`);
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setDetailOpen(false);
    setDetail(null);
  };

  const handleSubmit = async (id: number) => {
    setSubmitting(true);
    try {
      await PortraitAPI.submitHomeVisit(id);
      message.success('已提交审批');
      closeDetail();
      fetchList();
    } catch (err: any) {
      message.error(`提交失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id: number) => {
    setSubmitting(true);
    try {
      await PortraitAPI.cancelHomeVisit(id);
      message.success('已撤回');
      closeDetail();
      fetchList();
    } catch (err: any) {
      message.error(`撤回失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (id: number) => {
    setSubmitting(true);
    try {
      await PortraitAPI.approveHomeVisit(id, '');
      message.success('已审批通过');
      closeDetail();
      fetchList();
    } catch (err: any) {
      message.error(`通过失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const openRejectModal = (id: number) => {
    setRejectingId(id);
    rejectForm.resetFields();
    setRejectModalOpen(true);
  };

  const handleRejectConfirm = async () => {
    try {
      const { comment } = await rejectForm.validateFields();
      if (!rejectingId) return;
      setSubmitting(true);
      await PortraitAPI.rejectHomeVisit(rejectingId, comment);
      message.success('已驳回');
      setRejectModalOpen(false);
      setRejectingId(null);
      closeDetail();
      fetchList();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`驳回失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '被家访人',
      dataIndex: 'visited_name',
      key: 'visited_name',
      width: 100,
    },
    {
      title: 'EHR',
      dataIndex: 'visited_ehr_id',
      key: 'visited_ehr_id',
      width: 100,
    },
    {
      title: '家访年度',
      dataIndex: 'visit_year',
      key: 'visit_year',
      width: 100,
    },
    {
      title: '家访时间',
      dataIndex: 'visit_time',
      key: 'visit_time',
      width: 170,
    },
    {
      title: '家访人',
      dataIndex: 'visitor_name',
      key: 'visitor_name',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLOR[status] || 'default'}>{STATUS_LABEL[status] || status}</Tag>
      ),
    },
    {
      title: '当前审批人',
      dataIndex: 'current_approver_name',
      key: 'current_approver_name',
      width: 120,
      render: (v: string | null) => v || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: any, record: PortraitAPI.HomeVisitItem) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => openDetail(record.id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <BreadcrumbNav items={[{ title: '数字画像' }, { title: '家访' }]} />

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            家访记录
          </Title>
          <Text type="secondary">共 {total} 条</Text>
        </Space>

        <Tabs
          activeKey={statusFilter || 'all'}
          onChange={(k) => {
            setStatusFilter(k === 'all' ? undefined : k);
            setPage(1);
          }}
          items={[
            { key: 'all', label: '全部' },
            { key: 'draft', label: '草稿' },
            { key: 'pending', label: '审批中' },
            { key: 'approved', label: '已通过' },
            { key: 'rejected', label: '已驳回' },
            { key: 'cancelled', label: '已撤回' },
          ]}
        />

        <Space style={{ marginBottom: 12 }}>
          <Button icon={<ReloadOutlined />} onClick={fetchList}>
            刷新
          </Button>
        </Space>

        <Table
          loading={loading}
          dataSource={items}
          columns={columns}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            onChange: (p, s) => {
              setPage(p);
              setSize(s);
            },
          }}
        />
      </Card>

      <Modal
        title="家访详情"
        open={detailOpen}
        onCancel={closeDetail}
        footer={null}
        width={900}
        destroyOnClose
      >
        <Spin spinning={detailLoading}>
          {detail && (
            <>
              <Descriptions
                title="基本信息"
                bordered
                size="small"
                column={2}
                style={{ marginBottom: 16 }}
              >
                <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={STATUS_COLOR[detail.status]}>
                    {STATUS_LABEL[detail.status]}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="被家访人">{detail.visited_name}</Descriptions.Item>
                <Descriptions.Item label="EHR">{detail.visited_ehr_id}</Descriptions.Item>
                <Descriptions.Item label="家访人">{detail.visitor_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="年度">{detail.visit_year}</Descriptions.Item>
                <Descriptions.Item label="家访时间">{detail.visit_time}</Descriptions.Item>
                <Descriptions.Item label="方式">{detail.visit_method}</Descriptions.Item>
                <Descriptions.Item label="已家访">
                  {detail.is_visited ? '是' : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="家访地址" span={2}>
                  {detail.visit_address || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="岗位">{detail.position || '-'}</Descriptions.Item>
                <Descriptions.Item label="联系电话">
                  {detail.contact_phone || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="地址" span={2}>
                  {detail.address || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="手机">{detail.mobile || '-'}</Descriptions.Item>
                <Descriptions.Item label="家庭电话">
                  {detail.home_phone || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="家属1" span={2}>
                  {detail.family1_name || '-'} / {detail.family1_relation || '-'} /{' '}
                  {detail.family1_contact || '-'} / {detail.family1_work_unit || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="家属2" span={2}>
                  {detail.family2_name || '-'} / {detail.family2_relation || '-'} /{' '}
                  {detail.family2_contact || '-'} / {detail.family2_work_unit || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="反馈意见" span={2}>
                  {detail.feedback || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="提交时间">
                  {detail.submitted_at || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {detail.completed_at || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="当前审批人">
                  {detail.current_approver_name || '-'}
                </Descriptions.Item>
              </Descriptions>

              <Space>
                {detail.status === 'draft' && (
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    loading={submitting}
                    onClick={() => handleSubmit(detail.id)}
                  >
                    提交审批
                  </Button>
                )}
                {detail.status === 'pending' && (
                  <>
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      loading={submitting}
                      onClick={() => handleApprove(detail.id)}
                    >
                      通过
                    </Button>
                    <Button
                      danger
                      icon={<CloseOutlined />}
                      loading={submitting}
                      onClick={() => openRejectModal(detail.id)}
                    >
                      驳回
                    </Button>
                    <Popconfirm
                      title="确认撤回?"
                      onConfirm={() => handleCancel(detail.id)}
                    >
                      <Button icon={<RollbackOutlined />} loading={submitting}>
                        撤回
                      </Button>
                    </Popconfirm>
                  </>
                )}
              </Space>
            </>
          )}
        </Spin>
      </Modal>

      <Modal
        title="驳回家访"
        open={rejectModalOpen}
        onCancel={() => setRejectModalOpen(false)}
        onOk={handleRejectConfirm}
        confirmLoading={submitting}
        okText="确认驳回"
        okButtonProps={{ danger: true }}
      >
        <Form form={rejectForm} layout="vertical">
          <Form.Item
            name="comment"
            label="驳回理由 (必填)"
            rules={[{ required: true, message: '请填写驳回理由' }]}
          >
            <Input.TextArea rows={4} maxLength={500} showCount placeholder="说明驳回原因" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default HomeVisits;