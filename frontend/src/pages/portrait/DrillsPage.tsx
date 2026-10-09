/**
 * 数字画像-消防演练台账 (PRD §10.2 F2-F4)
 *
 * F2 演练登记 / F3 批量导入 / F4 参与矩阵 (紫色高亮列 #9370DB)
 * 权限: 写操作仅 admin; 其余只读.
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Select,
  Space,
  Drawer,
  Form,
  DatePicker,
  InputNumber,
  Input,
  message,
  Popconfirm,
  Tag,
  Typography,
  Upload,
  Tabs,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  DownloadOutlined,
  InboxOutlined,
  TableOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import dayjs from 'dayjs';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { useAuthStore } from '../../stores/authStore';
import { api } from '../../api';

const { Text, Title } = Typography;
const { Dragger } = Upload;

const PURPLE = '#9370DB';  // PRD F4 矩阵参与高亮色

const DrillPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('list');
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<PortraitAPI.DrillRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [drillType, setDrillType] = useState<string | undefined>();
  const [matrix, setMatrix] = useState<PortraitAPI.DrillMatrix | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [drawer, setDrawer] = useState<'create' | { type: 'view'; record: PortraitAPI.DrillDetail } | null>(null);
  const [detail, setDetail] = useState<PortraitAPI.DrillDetail | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [users, setUsers] = useState<PortraitAPI.ApproverUser[]>([]);

  const isAdmin = useAuthStore.getState().user?.roles?.includes('admin')
    || useAuthStore.getState().user?.permissions?.includes('*:*') || false;

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await PortraitAPI.getDrillRecords({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        drill_type: drillType,
      });
      setRecords(resp.items);
      setTotal(resp.total);
    } catch (err: any) {
      message.error(`加载演练记录失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, drillType]);

  const fetchMatrix = useCallback(async () => {
    setMatrixLoading(true);
    try {
      setMatrix(await PortraitAPI.getDrillMatrix());
    } catch (err: any) {
      message.error(`加载演练矩阵失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setMatrixLoading(false);
    }
  }, []);

  // 参与者下拉数据
  const fetchUsers = useCallback(async () => {
    try {
      const resp = await PortraitAPI.listUsersForApprover({ limit: 500 });
      setUsers(resp.items);
    } catch { /* 静默: 下拉为空时仍可手填 */ }
  }, []);

  useEffect(() => { fetchList(); }, [fetchList]);
  useEffect(() => { if (activeTab === 'matrix') fetchMatrix(); }, [activeTab, fetchMatrix]);
  useEffect(() => { if (isAdmin) fetchUsers(); }, [isAdmin, fetchUsers]);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ activity_date: dayjs() });
    setDrawer('create');
  };

  const openView = async (id: number) => {
    try {
      const d = await PortraitAPI.getDrillDetail(id);
      setDetail(d);
      setDrawer({ type: 'view', record: d });
    } catch (err: any) {
      message.error(`加载详情失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload: PortraitAPI.DrillCreate = {
        activity_date: values.activity_date.format('YYYY-MM-DD'),
        drill_type: values.drill_type,
        location: values.location,
        duration_minutes: values.duration_minutes ?? null,
        participant_ehr_ids: values.participant_ehr_ids || [],
      };
      setSaving(true);
      await PortraitAPI.createDrill(payload);
      message.success('演练已登记');
      setDrawer(null);
      fetchList();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(`登记失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await PortraitAPI.deleteDrill(id);
      message.success('已删除');
      fetchList();
    } catch (err: any) {
      message.error(`删除失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const downloadTemplate = async () => {
    try {
      const response = await api.get('/portrait/templates/excel/drill', { responseType: 'blob' });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '消防演练_导入模板.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('模板下载已开始');
    } catch (err: any) {
      message.error(`模板下载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const importProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls,.csv',
    multiple: false,
    showUploadList: false,
    beforeUpload: async (file: UploadFile) => {
      setImporting(true);
      try {
        const result = await PortraitAPI.importDrill(file as unknown as File);
        if (result.failed_count === 0) message.success(`导入成功: ${result.success_count} 条`);
        else if (result.success_count === 0) message.error(`导入失败: ${result.failed_count} 条全部失败`);
        else message.warning(`部分成功: ${result.success_count} 条, 失败 ${result.failed_count} 条`);
        if (result.failed_count > 0) {
          // Rule 12: 失败显性化
          console.table(result.failed_rows.map((f) => ({ 行号: f.row_number, EHR: f.ehr_id, 原因: f.reason })));
        }
        fetchList();
      } catch (err: any) {
        message.error(`导入失败: ${err?.response?.data?.detail || err.message}`);
      } finally {
        setImporting(false);
      }
      return false;
    },
  };

  // 矩阵列头
  const matrixColumns: any[] = [
    { title: '团队', dataIndex: 'team_name', width: 120, fixed: 'left' },
    { title: '姓名', dataIndex: 'name', width: 100, fixed: 'left' },
    { title: '职务', dataIndex: 'position', width: 100, fixed: 'left', render: (v: string) => v || '—' },
    ...(matrix?.columns || []).map((col, i) => ({
      title: (
        <div>
          <div>{col.activity_date}</div>
          <Tag color={PURPLE} style={{ marginTop: 4 }}>{col.drill_type}</Tag>
          <div style={{ fontSize: 11, color: '#999', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis' }}>{col.location}</div>
        </div>
      ),
      key: `c${i}`,
      width: 96,
      align: 'center' as const,
      render: (_v: any, row: PortraitAPI.MatrixRow) => {
        const cell = row.cells[i];
        return cell?.participated
          ? <span style={{ background: PURPLE, color: '#fff', padding: '2px 10px', borderRadius: 4, fontWeight: 600 }}>{cell.value}</span>
          : <span style={{ color: '#bbb' }}>{cell?.value || '—'}</span>;
      },
    })),
    { title: '参与场次', dataIndex: 'participated_count', width: 90, align: 'center' as const, fixed: 'right' },
  ];

  return (
    <div>
      <BreadcrumbNav
        items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '消防演练' }]}
      />
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>消防演练台账 (F2-F4)</Title>
            <Text type="secondary">PRD §10.2</Text>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={downloadTemplate} disabled={!isAdmin}>下载模板</Button>
            <Upload {...importProps}>
              <Button icon={<InboxOutlined />} disabled={!isAdmin} loading={importing}>批量导入 (F3)</Button>
            </Upload>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} disabled={!isAdmin}>演练登记 (F2)</Button>
            <Button icon={<ReloadOutlined />} onClick={() => activeTab === 'matrix' ? fetchMatrix() : fetchList()} loading={loading || matrixLoading}>刷新</Button>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'list',
              label: <span><TableOutlined /> 演练记录</span>,
              children: (
                <>
                  <Space style={{ marginBottom: 16 }}>
                    <Select
                      placeholder="演练类型筛选"
                      allowClear
                      style={{ width: 160 }}
                      value={drillType}
                      onChange={setDrillType}
                      options={[
                        { value: '演练', label: '演练' },
                        { value: '培训', label: '培训' },
                        { value: '应急疏散', label: '应急疏散' },
                      ]}
                    />
                  </Space>
                  <Table
                    rowKey="id"
                    loading={loading}
                    dataSource={records}
                    pagination={{
                      current: page,
                      pageSize,
                      total,
                      showTotal: (t) => `共 ${t} 条`,
                      onChange: (p, s) => { setPage(p); setPageSize(s); },
                    }}
                    columns={[
                      { title: '活动日期', dataIndex: 'activity_date', width: 110 },
                      { title: '类型', dataIndex: 'drill_type', width: 100, render: (v: string) => <Tag color={PURPLE}>{v}</Tag> },
                      { title: '地点', dataIndex: 'location', ellipsis: true },
                      { title: '时长(分)', dataIndex: 'duration_minutes', width: 90, render: (v: number | null) => v ?? '—' },
                      { title: '参与人数', dataIndex: 'participant_count', width: 90, align: 'center' },
                      {
                        title: '操作',
                        width: 140,
                        render: (_v, r: PortraitAPI.DrillRecord) => (
                          <Space>
                            <Button size="small" icon={<EyeOutlined />} onClick={() => openView(r.id)}>详情</Button>
                            {isAdmin && (
                              <Popconfirm title="删除该演练及其参与记录?" onConfirm={() => handleDelete(r.id)}>
                                <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                              </Popconfirm>
                            )}
                          </Space>
                        ),
                      },
                    ]}
                    scroll={{ x: 900 }}
                  />
                </>
              ),
            },
            {
              key: 'matrix',
              label: <span><PartitionOutlined /> 参与矩阵 (F4)</span>,
              children: (
                <>
                  <Space style={{ marginBottom: 12 }}>
                    <Text type="secondary">行=参与员工, 列=每场演练, <span style={{ background: PURPLE, color: '#fff', padding: '0 6px', borderRadius: 3 }}>紫色</span>=已参与</Text>
                  </Space>
                  <Table
                    rowKey="ehr_id"
                    loading={matrixLoading}
                    dataSource={matrix?.rows || []}
                    columns={matrixColumns}
                    scroll={{ x: 300 + (matrix?.columns.length || 0) * 96, y: 480 }}
                    pagination={false}
                    summary={() => (
                      <Table.Summary.Row>
                        <Table.Summary.Cell index={0} colSpan={3}><b>合计</b></Table.Summary.Cell>
                        {matrix?.columns.map((_c, i) => (
                          <Table.Summary.Cell index={i + 3} key={i} align="center">
                            {matrix.rows.filter((r) => r.cells[i]?.participated).length}
                          </Table.Summary.Cell>
                        ))}
                        <Table.Summary.Cell index={999} align="center"><b>{matrix?.rows.length || 0}</b></Table.Summary.Cell>
                      </Table.Summary.Row>
                    )}
                  />
                  <Divider />
                  <Text type="secondary">共 {matrix?.total_drills ?? 0} 场演练, 涉及 {matrix?.total_participants ?? 0} 名员工</Text>
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* F2 登记抽屉 */}
      <Drawer
        title="演练登记 (F2)"
        width={480}
        open={drawer === 'create'}
        onClose={() => setDrawer(null)}
        extra={<Button type="primary" loading={saving} onClick={handleSave}>保存</Button>}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="活动日期 *" name="activity_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="演练类型 *" name="drill_type" rules={[{ required: true }]}>
            <Select options={[
              { value: '演练', label: '演练' },
              { value: '培训', label: '培训' },
              { value: '应急疏散', label: '应急疏散' },
            ]} />
          </Form.Item>
          <Form.Item label="地点 *" name="location" rules={[{ required: true }]}>
            <Input placeholder="例如: 总行办公大楼 1 楼大厅" />
          </Form.Item>
          <Form.Item label="时长(分钟)" name="duration_minutes">
            <InputNumber min={0} style={{ width: '100%' }} placeholder="选填" />
          </Form.Item>
          <Form.Item label="参与人员 (按 EHR 号勾选)" name="participant_ehr_ids">
            <Select
              mode="multiple"
              placeholder="选择参与本次演练的员工"
              optionFilterProp="label"
              options={users.map((u) => ({ value: u.ehr_id, label: `${u.name} (${u.ehr_id})` }))}
            />
          </Form.Item>
        </Form>
      </Drawer>

      {/* F4 详情抽屉 */}
      <Drawer
        title={detail ? `演练详情 #${detail.id}` : '演练详情'}
        width={520}
        open={drawer?.type === 'view'}
        onClose={() => setDrawer(null)}
      >
        {detail && (
          <>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text>活动日期: {detail.activity_date}</Text>
              <Text>类型: <Tag color={PURPLE}>{detail.drill_type}</Tag></Text>
              <Text>地点: {detail.location}</Text>
              <Text>时长: {detail.duration_minutes ?? '—'} 分钟</Text>
              <Text>参与人数: {detail.participants.length}</Text>
            </Space>
            <Divider>参与人员</Divider>
            <Table
              rowKey="id"
              size="small"
              dataSource={detail.participants}
              pagination={false}
              columns={[
                { title: '姓名', dataIndex: 'name', width: 100 },
                { title: 'EHR号', dataIndex: 'ehr_id', width: 100 },
                { title: '参与', dataIndex: 'participated', width: 60, render: (v: boolean) => (v ? <Tag color={PURPLE}>是</Tag> : <Tag>否</Tag>) },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  );
};

export default DrillPage;
