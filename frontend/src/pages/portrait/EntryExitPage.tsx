/**
 * 数字画像-出入境台账 (PRD §10.1 F5-F9)
 *
 * F5 列表: 分页 + 筛选 + 年份高亮 + 顶部 4 统计卡
 * F6 新增 / F7 查看 / F8 编辑 / F9 批量导入
 *
 * 权限: 写操作仅 admin; 员工只读自己, 组长看本组.
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Statistic,
  Row,
  Col,
  Drawer,
  Form,
  DatePicker,
  InputNumber,
  message,
  Popconfirm,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  InboxOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import dayjs from 'dayjs';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { useAuthStore } from '../../stores/authStore';
import { api } from '../../api';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;
const { Dragger } = Upload;

interface ImportResult {
  success_count: number;
  failed_count: number;
  failed_rows: Array<{ row_number: number; ehr_id: string; reason: string }>;
}

type DrawerMode =
  | { type: 'create' }
  | { type: 'edit'; record: PortraitAPI.EntryExitRecord }
  | { type: 'view'; record: PortraitAPI.EntryExitRecord };

const EntryExitPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<PortraitAPI.EntryExitRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [statistics, setStatistics] = useState<PortraitAPI.EntryExitStatistics | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filters, setFilters] = useState<{ name?: string; year?: number }>({});
  const [drawer, setDrawer] = useState<DrawerMode | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [importModal, setImportModal] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importing, setImporting] = useState(false);

  // is_admin 从登录态判断 (与后端 /me/permissions 一致)
  const isAdmin = useAuthStore.getState().user?.roles?.includes('admin')
    || useAuthStore.getState().user?.permissions?.includes('*:*') || false;

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await PortraitAPI.getEntryExitRecords({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        name: filters.name || undefined,
        year: filters.year,
        stats: true,
      });
      setRecords(resp.items);
      setTotal(resp.total);
      setStatistics(resp.statistics || null);
    } catch (err: any) {
      message.error(`加载出入境记录失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ year: new Date().getFullYear() });
    setDrawer({ type: 'create' });
  };

  const openEdit = (record: PortraitAPI.EntryExitRecord) => {
    form.resetFields();
    form.setFieldsValue({
      ...record,
      apply_depart_at: record.apply_depart_at ? dayjs(record.apply_depart_at) : null,
      apply_return_at: record.apply_return_at ? dayjs(record.apply_return_at) : null,
      actual_depart_at: record.actual_depart_at ? dayjs(record.actual_depart_at) : null,
      actual_return_at: record.actual_return_at ? dayjs(record.actual_return_at) : null,
    });
    setDrawer({ type: 'edit', record });
  };

  const openView = (record: PortraitAPI.EntryExitRecord) => {
    setDrawer({ type: 'view', record });
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload: PortraitAPI.EntryExitCreate = {
        ...values,
        apply_depart_at: values.apply_depart_at?.format('YYYY-MM-DD HH:mm:ss') || values.apply_depart_at,
        apply_return_at: values.apply_return_at?.format('YYYY-MM-DD HH:mm:ss') || values.apply_return_at,
        actual_depart_at: values.actual_depart_at?.format('YYYY-MM-DD HH:mm:ss') || values.actual_depart_at || null,
        actual_return_at: values.actual_return_at?.format('YYYY-MM-DD HH:mm:ss') || values.actual_return_at || null,
      };
      setSaving(true);
      if (drawer?.type === 'create') {
        await PortraitAPI.createEntryExit(payload);
        message.success('出入境记录已新增');
      } else if (drawer?.type === 'edit') {
        await PortraitAPI.updateEntryExit(drawer.record.id, payload);
        message.success('出入境记录已更新');
      }
      setDrawer(null);
      fetchList();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`保存失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await PortraitAPI.deleteEntryExit(id);
      message.success('已删除');
      fetchList();
    } catch (err: any) {
      message.error(`删除失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const downloadTemplate = async () => {
    try {
      const response = await api.get('/portrait/templates/excel/entry-exit', { responseType: 'blob' });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '出入境台账_导入模板.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('模板下载已开始');
    } catch (err: any) {
      message.error(`模板下载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const importUploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls,.csv',
    multiple: false,
    showUploadList: false,
    beforeUpload: async (file: UploadFile) => {
      setImporting(true);
      setImportResult(null);
      try {
        const result = await PortraitAPI.importEntryExit(file as unknown as File);
        setImportResult(result);
        if (result.failed_count === 0) message.success(`导入成功: ${result.success_count} 条`);
        else if (result.success_count === 0) message.error(`导入失败: ${result.failed_count} 条全部失败`);
        else message.warning(`部分成功: ${result.success_count} 条, 失败 ${result.failed_count} 条`);
        fetchList();
      } catch (err: any) {
        message.error(`导入失败: ${err?.response?.data?.detail || err.message}`);
      } finally {
        setImporting(false);
      }
      return false;  // 阻止 antd 默认上传
    },
  };

  // 当前年份高亮
  const currentYear = new Date().getFullYear();

  return (
    <div>
      <BreadcrumbNav
        items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '出入境台账' }]}
      />
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>出入境台账 (F5)</Title>
            <Text type="secondary">PRD §10.1</Text>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={downloadTemplate} disabled={!isAdmin}>
              下载模板
            </Button>
            <Upload {...importUploadProps}>
              <Button icon={<InboxOutlined />} disabled={!isAdmin} loading={importing}>
                批量导入 (F9)
              </Button>
            </Upload>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openCreate}
              disabled={!isAdmin}
            >
              新增 (F6)
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchList()} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        {/* 顶部统计卡 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small"><Statistic title="累计记录" value={statistics?.total_count ?? 0} /></Card>
          </Col>
          <Col span={6}>
            <Card size="small"><Statistic title="本年度" value={statistics?.current_year_count ?? 0} /></Card>
          </Col>
          <Col span={6}>
            <Card size="small"><Statistic title="已关联证照" value={statistics?.distinct_certificate_count ?? 0} /></Card>
          </Col>
          <Col span={6}>
            <Card size="small"><Statistic title="实际未返回" value={statistics?.not_returned_count ?? 0} valueStyle={{ color: '#ff4d4f' }} /></Card>
          </Col>
        </Row>

        {/* 筛选条 */}
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="姓名搜索"
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 180 }}
            onChange={(e) => setFilters((f) => ({ ...f, name: e.target.value || undefined }))}
          />
          <InputNumber
            placeholder="年份"
            min={2000}
            max={2100}
            style={{ width: 120 }}
            onChange={(v) => setFilters((f) => ({ ...f, year: v ?? undefined }))}
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={() => { setPage(1); fetchList(); }}
          >
            查询
          </Button>
        </Space>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={records}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, s) => { setPage(p); setPageSize(s); },
          }}
          columns={[
            { title: '序号', width: 60, render: (_v, _r, i) => (page - 1) * pageSize + i + 1 },
            { title: '姓名', dataIndex: 'name', width: 90 },
            { title: '团队', dataIndex: 'team_name', width: 130 },
            { title: '证照号', dataIndex: 'certificate_no', width: 110 },
            { title: '出境原因', dataIndex: 'outbound_reason', ellipsis: true },
            { title: '目的地', dataIndex: 'destination', width: 100 },
            { title: '申请离境', dataIndex: 'apply_depart_at', width: 100, render: (v) => v?.slice(0, 10) },
            { title: '申请返回', dataIndex: 'apply_return_at', width: 100, render: (v) => v?.slice(0, 10) },
            {
              title: '年份',
              dataIndex: 'year',
              width: 80,
              render: (v: number) => (
                <Tag color={v === currentYear ? '#faad14' : undefined} style={v === currentYear ? { background: '#fff3cd' } : undefined}>
                  {v}{v === currentYear ? ' (本年)' : ''}
                </Tag>
              ),
            },
            {
              title: '操作',
              width: 160,
              render: (_v, record: PortraitAPI.EntryExitRecord) => (
                <Space>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => openView(record)}>查看</Button>
                  {isAdmin && (
                    <>
                      <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
                      <Popconfirm title="确定删除该记录?" onConfirm={() => handleDelete(record.id)}>
                        <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                      </Popconfirm>
                    </>
                  )}
                </Space>
              ),
            },
          ]}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 新增/编辑/查看抽屉 */}
      <Drawer
        title={drawer?.type === 'create' ? '新增出入境记录 (F6)' : drawer?.type === 'edit' ? '编辑出入境记录 (F8)' : '出入境记录详情 (F7)'}
        width={720}
        open={!!drawer}
        onClose={() => setDrawer(null)}
        extra={
          drawer?.type !== 'view' && isAdmin ? (
            <Button type="primary" loading={saving} onClick={handleSave}>
              保存
            </Button>
          ) : null
        }
      >
        {drawer?.type === 'view' && drawer.record ? (
          <RenderDetail record={drawer.record} />
        ) : (
          <Form form={form} layout="vertical">
            <Row gutter={16}>
              <Col span={12}><Form.Item label="EHR号" name="ehr_id" rules={[{ required: true }, { pattern: /^\d{7}$/, message: '恰好 7 位数字' }]}><Input disabled={drawer?.type === 'edit'} placeholder="7 位数字" /></Form.Item></Col>
              <Col span={12}><Form.Item label="姓名 *" name="name" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="团队 *" name="team_name" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="职务 *" name="position" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="证照号 *" name="certificate_no" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="证照类别 *" name="certificate_type" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="申请类型 *" name="apply_type" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="团队审批人 *" name="team_approver" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={24}><Form.Item label="出境原因 *" name="outbound_reason" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item></Col>
              <Col span={12}><Form.Item label="目的地 *" name="destination" rules={[{ required: true }]}><Input /></Form.Item></Col>
              <Col span={12}><Form.Item label="年份 *" name="year" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={2000} max={2100} /></Form.Item></Col>
              <Col span={12}><Form.Item label="申请离境 *" name="apply_depart_at" rules={[{ required: true }]}><DatePicker showTime style={{ width: '100%' }} /></Form.Item></Col>
              <Col span={12}><Form.Item label="申请返回 *" name="apply_return_at" rules={[{ required: true }]}><DatePicker showTime style={{ width: '100%' }} /></Form.Item></Col>
              <Col span={12}><Form.Item label="实际出境" name="actual_depart_at"><DatePicker showTime style={{ width: '100%' }} /></Form.Item></Col>
              <Col span={12}><Form.Item label="实际返回" name="actual_return_at"><DatePicker showTime style={{ width: '100%' }} /></Form.Item></Col>
              <Col span={12}><Form.Item label="组别" name="group_name"><Input /></Form.Item></Col>
              <Col span={24}><Form.Item label="备注" name="remark"><Input.TextArea rows={2} /></Form.Item></Col>
            </Row>
          </Form>
        )}
      </Drawer>
    </div>
  );
};

// 只读详情渲染
const RenderDetail: React.FC<{ record: PortraitAPI.EntryExitRecord }> = ({ record }) => {
  const items: Array<[string, React.ReactNode]> = [
    ['EHR号', record.ehr_id],
    ['姓名', record.name],
    ['团队', record.team_name],
    ['职务', record.position],
    ['证照号', record.certificate_no],
    ['证照类别', record.certificate_type],
    ['申请类型', record.apply_type],
    ['团队审批人', record.team_approver],
    ['出境原因', record.outbound_reason],
    ['目的地', record.destination],
    ['年份', record.year],
    ['申请离境', record.apply_depart_at?.slice(0, 16)],
    ['申请返回', record.apply_return_at?.slice(0, 16)],
    ['实际出境', record.actual_depart_at?.slice(0, 16) || '—'],
    ['实际返回', record.actual_return_at?.slice(0, 16) || '—'],
    ['组别', record.group_name || '—'],
    ['备注', record.remark || '—'],
  ];
  return (
    <Row gutter={[16, 12]}>
      {items.map(([label, value]) => (
        <Col span={12} key={label}>
          <Text type="secondary">{label}</Text>
          <div style={{ fontWeight: 500 }}>{value}</div>
        </Col>
      ))}
    </Row>
  );
};

export default EntryExitPage;