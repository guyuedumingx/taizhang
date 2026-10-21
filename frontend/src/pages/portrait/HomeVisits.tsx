/**
 * 数字画像-家访 (P6 阶段, 批次 11; C1 升级, 批次 17)
 *
 * PRD §C §9.1: 家访审批流 (4 类审批共用审批工作台模式)
 * C1 (PRD §7.1): 组长填家访表单完整版 — 双人员家访 + 扫描件 + 团队名称
 *
 * 集成指南 §5 雷区 7: 不绕过 Depends — 所有更新走 api
 * 集成指南 §5 雷区 12: reject 必须填 comment, 显式 400
 *
 * MVP 范围:
 *  - 列表 (status/visit_year/visited_ehr_id 筛选)
 *  - 详情查看 (含 22 + 3 字段)
 *  - 审批操作: 通过 (admin/current_approver) / 驳回 (admin/current_approver, 必须 comment) / 撤回 (仅 visitor, 仅 pending)
 *  - 草稿提交 (仅 visitor)
 *  - C1: 新建家访两步表单 (Step1 明细 / Step2 记录表)
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
  Upload,
  Select,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  RollbackOutlined,
  SendOutlined,
  PlusOutlined,
  EditOutlined,
  DownloadOutlined,
  InboxOutlined,
  PrinterOutlined,
  FilePdfOutlined,
  TableOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import * as PortraitAPI from '../../api/portrait';
import { useAuthStore } from '../../stores/authStore';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import CreateHomeVisitModal from './CreateHomeVisitModal';

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

  // Week 3 P0.3: 编辑模式 state
  const [editingRecord, setEditingRecord] = useState<PortraitAPI.HomeVisitDetail | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);

  // C1: 新建家访
  const { user } = useAuthStore();
  const [createOpen, setCreateOpen] = useState(false);
  // 同组成员下拉数据 (取所有用户, 前端按需过滤)
  const [teamMembers, setTeamMembers] = useState<Array<{ id: number; name: string; ehr_id: string; team_id: number | null }>>([]);

  // 决策 1 (2026-10-16): 组长身份由后端口径决定 —— 我所在组的 teams.leader_id 就是我。
  // 前端不再用 "user.teamId 非空" 猜组长 (那等于"分到组就是组长"), 而是读后端
  // /portrait/me/permissions 的 is_leader, 与 service 层 TeamService.is_leader 同源。
  // 后端 is_leader 对超管恒为 False —— 超管的"管理员"身份走 isAdmin 分支。
  const [isLeader, setIsLeader] = useState(false);
  // 后端 superuser 返回的权限串是 "*:*" (users.py:270), 从不是 "*"
  const isAdmin = !!(user?.permissions || []).includes('*:*');

  useEffect(() => {
    if (!user) return;
    PortraitAPI.getMyPermissions()
      .then((p) => setIsLeader(!!p.is_leader))
      .catch((err) => {
        // Rule 12: 失败必须显性化 —— 取不到组长身份时按"非组长"降级并报错,
        // 不能静默当成组长 (会给不该有权限的人显示按钮)。
        setIsLeader(false);
        console.error('获取当前用户画像权限失败:', err);
        message.error('获取当前用户权限失败, 组长功能入口已隐藏, 请刷新重试');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  // 是否可创建家访 (仅组长)。业务规则"谁做家访谁签字" → 管理员也不可创建,
  // 后端 create_draft 对超管显式 403, 前端不给入口 (后端才是安全边界)。
  const canCreate = isLeader;
  // F11 导入与"家访新建"同一套权限 (组长), 管理员同样不可导入。
  const canImport = isLeader;
  // §13 家访批量导出 Excel: 员工 ❌ / 组长 ✅ / 管理员 ✅
  const canExport = isLeader || isAdmin;

  // ---------------------------------------------------------------- F11/F12
  const [importing, setImporting] = useState(false);
  const [pageTab, setPageTab] = useState('list');
  const [matrix, setMatrix] = useState<PortraitAPI.HomeVisitMatrix | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [matrixTeam, setMatrixTeam] = useState<string | undefined>(undefined);
  const [matrixIncludePending, setMatrixIncludePending] = useState(true);
  // 打印 / 导出 PDF (C3)
  const [printOpen, setPrintOpen] = useState(false);

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

  // C1: 加载同组成员 (用于"被家访人"和"第二家访人"下拉)
  const fetchTeamMembers = async () => {
    try {
      const { getUserMembers } = await import('../../api/users');
      // 走 /users/members 最小接口: 任意登录用户可用, 且不暴露部门/角色/管理员标记。
      // 该接口返回的是数组 (不是 getUsers 的分页对象)。
      const allMembers = await getUserMembers({ limit: 500 });
      setTeamMembers(
        allMembers.map((u) => ({
          id: u.id,
          name: u.name || '',
          ehr_id: u.ehr_id || '',
          team_id: u.team_id,
        }))
      );
    } catch (err: any) {
      // Rule 12: 失败必须显性化, 不能只 console.error 静默吞掉
      // (静默会导致下拉框为空, 用户只看到"没有选项"而无从判断原因)
      console.error('加载成员失败:', err);
      message.warning('加载团队成员失败, 被家访人下拉框可能为空, 请手动输入 EHR 号回填');
    }
  };

  useEffect(() => {
    if (createOpen && teamMembers.length === 0) {
      fetchTeamMembers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createOpen]);

  // ------------------------------------------------------------------ F12 矩阵
  const fetchMatrix = async () => {
    setMatrixLoading(true);
    try {
      setMatrix(
        await PortraitAPI.getHomeVisitMatrix({
          team_name: matrixTeam,
          include_pending: matrixIncludePending,
        })
      );
    } catch (err: any) {
      message.error(`加载家访矩阵失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setMatrixLoading(false);
    }
  };

  useEffect(() => {
    if (pageTab === 'matrix') fetchMatrix();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageTab, matrixTeam, matrixIncludePending]);

  // 团队下拉候选项: 从已加载矩阵的行里取, 不另开接口
  const matrixTeamOptions = React.useMemo(() => {
    const set = new Set<string>();
    (matrix?.rows || []).forEach((r) => {
      if (r.team_name) set.add(r.team_name);
    });
    return Array.from(set).sort();
  }, [matrix]);

  // ------------------------------------------------------------- F11 批量导入
  const importProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls,.csv',
    multiple: false,
    showUploadList: false,
    beforeUpload: async (file: UploadFile) => {
      setImporting(true);
      try {
        const result = await PortraitAPI.importHomeVisits(file as unknown as File);
        if (result.failed_count === 0) {
          message.success(`导入成功: ${result.success_count} 条`);
        } else if (result.success_count === 0) {
          message.error(`导入失败: ${result.failed_count} 条全部失败`);
        } else {
          message.warning(
            `部分成功: ${result.success_count} 条, 失败 ${result.failed_count} 条`
          );
        }
        // Rule 12: 失败必须显性化, 且要让业务人员看得懂是谁的哪一行没导进去
        if (result.failed_count > 0) {
          Modal.error({
            title: `导入失败明细 (共 ${result.failed_count} 行)`,
            width: 720,
            content: (
              <Table
                size="small"
                rowKey="row_number"
                pagination={false}
                dataSource={result.failed_rows}
                scroll={{ y: 360 }}
                columns={[
                  { title: '行号', dataIndex: 'row_number', width: 70 },
                  { title: 'EHR号', dataIndex: 'ehr_id', width: 110, render: (v: string) => v || '—' },
                  { title: '原因', dataIndex: 'reason' },
                ]}
              />
            ),
          });
        }
        fetchList();
        if (pageTab === 'matrix') fetchMatrix();
      } catch (err: any) {
        message.error(`导入失败: ${err?.response?.data?.detail || err.message}`);
      } finally {
        setImporting(false);
      }
      return false;
    },
  };

  const handleDownloadTemplate = async () => {
    try {
      await PortraitAPI.downloadHomeVisitTemplate();
      message.success('模板下载已开始');
    } catch (err: any) {
      message.error(`模板下载失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  // ------------------------------------------------------------------ 导出 Excel
  const handleExport = async () => {
    try {
      const { filename } = await PortraitAPI.exportHomeVisitsExcel({
        status: statusFilter,
      });
      message.success(`已导出 ${filename}`);
    } catch (err: any) {
      message.error(`导出失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

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

  // Week 3 P0.3: 打开编辑模式 (draft 状态才允许)
  const openEditModal = (record: PortraitAPI.HomeVisitDetail) => {
    setEditingRecord(record);
    setEditModalOpen(true);
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

  // F12 矩阵列 (PRD 附录 B.2): 行 = 员工, 列 = 年份, 单元格 = 该年具体家访日期。
  // §7.2 写"仅绿色", B.2 写"填具体日期" —— 两者不冲突: 日期是数据, 绿色是呈现。
  const matrixColumns: any[] = [
    { title: '序号', dataIndex: 'seq', width: 60, fixed: 'left' },
    { title: '姓名', dataIndex: 'name', width: 100, fixed: 'left' },
    { title: 'EHR号', dataIndex: 'ehr_id', width: 100, fixed: 'left' },
    { title: '分组', dataIndex: 'team_name', width: 120, fixed: 'left', render: (v: string) => v || '—' },
    ...(matrix?.columns || []).map((col, i) => ({
      title: `家访日期 ${col.year}`,
      key: `y${i}`,
      width: 130,
      align: 'center' as const,
      render: (_v: any, row: PortraitAPI.HomeVisitMatrixRow) => {
        const cell = row.cells[i];
        return cell?.value ? (
          <span
            style={{
              background: '#52C41A',
              color: '#fff',
              padding: '2px 8px',
              borderRadius: 4,
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            {cell.value}
          </span>
        ) : (
          <span style={{ color: '#ccc' }}>—</span>
        );
      },
    })),
    {
      title: '家访年度',
      dataIndex: 'visited_years',
      width: 160,
      fixed: 'right',
      render: (v: string) => v || <span style={{ color: '#ccc' }}>未家访</span>,
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
          activeKey={pageTab}
          onChange={setPageTab}
          items={[
            { key: 'list', label: <span><TableOutlined /> 记录列表</span> },
            { key: 'matrix', label: <span><PartitionOutlined /> 年度矩阵 (F12)</span> },
          ]}
        />

      {pageTab === 'list' && (
      <>
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

        <Space style={{ marginBottom: 12 }} wrap>
          <Button icon={<ReloadOutlined />} onClick={fetchList}>
            刷新
          </Button>
          {canCreate && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateOpen(true)}
            >
              新建家访
            </Button>
          )}
          {canImport && (
            <>
              <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
                下载模板 (F11)
              </Button>
              <Upload {...importProps}>
                <Button icon={<InboxOutlined />} loading={importing}>
                  批量导入 (F11)
                </Button>
              </Upload>
            </>
          )}
          {canExport && (
            <Tooltip title="导出当前状态筛选下的全部记录, 列与导入模板一致">
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                导出 Excel
              </Button>
            </Tooltip>
          )}
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
      </>
      )}

      {pageTab === 'matrix' && (
        <>
          <Space style={{ marginBottom: 12 }} wrap>
            <Text type="secondary">
              行=员工, 列=年份, <span style={{ background: '#52C41A', color: '#fff', padding: '0 6px', borderRadius: 3 }}>绿色</span>=该年已家访
            </Text>
            <Select
              allowClear
              showSearch
              placeholder="全部分组"
              style={{ width: 180 }}
              optionFilterProp="label"
              value={matrixTeam}
              onChange={setMatrixTeam}
              options={matrixTeamOptions.map((t) => ({ label: t, value: t }))}
            />
            <Tooltip title="关掉后只统计审批通过的记录; 草稿/驳回/撤回一律不计入">
              <Select
                style={{ width: 200 }}
                value={matrixIncludePending ? 'with' : 'only'}
                onChange={(v) => setMatrixIncludePending(v === 'with')}
                options={[
                  { label: '含审批中记录', value: 'with' },
                  { label: '仅统计已通过记录', value: 'only' },
                ]}
              />
            </Tooltip>
            <Button icon={<ReloadOutlined />} onClick={fetchMatrix} loading={matrixLoading}>
              刷新
            </Button>
          </Space>

          <Table
            rowKey="ehr_id"
            size="small"
            loading={matrixLoading}
            dataSource={matrix?.rows || []}
            columns={matrixColumns}
            scroll={{ x: 310 + (matrix?.columns.length || 0) * 130, y: 520 }}
            pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `共 ${t} 人` }}
            summary={() => (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={4}><b>已家访人数</b></Table.Summary.Cell>
                {(matrix?.columns || []).map((_c, i) => (
                  <Table.Summary.Cell index={i + 4} key={i} align="center">
                    {(matrix?.rows || []).filter((r) => r.cells[i]?.value).length}
                  </Table.Summary.Cell>
                ))}
                <Table.Summary.Cell index={999} align="center">
                  <b>{matrix?.total_visited_users ?? 0}</b>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            )}
          />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              共 {matrix?.total_years ?? 0} 个年度, 被家访过 {matrix?.total_visited_users ?? 0} 人
              （空白行 = 从未被家访, 这正是这张表要盯出来的人）
            </Text>
          </div>
        </>
      )}
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
                <Descriptions.Item label="第二家访人">{detail.co_visitor_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="年度">{detail.visit_year}</Descriptions.Item>
                <Descriptions.Item label="团队名称">{detail.team_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="家访时间">{detail.visit_time}</Descriptions.Item>
                <Descriptions.Item label="方式">{detail.visit_method}</Descriptions.Item>
                <Descriptions.Item label="已家访">
                  {detail.is_visited ? '是' : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="家访地址" span={2}>
                  {detail.visit_address || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="岗位">{detail.position || '-'}</Descriptions.Item>
                <Descriptions.Item label="反馈意见" span={2}>
                  {detail.feedback || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="提交时间">
                  {detail.submitted_at || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {detail.completed_at || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="扫描件" span={2}>
                  {detail.scan_file_url ? (
                    <a href={detail.scan_file_url} target="_blank" rel="noopener noreferrer">
                      {detail.scan_file_path}
                    </a>
                  ) : (
                    '-'
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="记录表扫描件状态" span={2}>
                  {/* PRD 附录 B.4 第 14 列, 与上面的电子文件是两件事 */}
                  <Tag color={detail.scan_status === '已提交' ? 'green' : 'default'}>
                    {detail.scan_status || '未提交'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="家访人员及岗位" span={2}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {detail.visitor_info || '-'}
                  </pre>
                </Descriptions.Item>
                <Descriptions.Item label="当前审批人">
                  {detail.current_approver_name || '-'}
                </Descriptions.Item>
              </Descriptions>

              <Space wrap>
                {/* C3 (PRD §7.3): 预览打印 / 导出 PDF。
                    PDF 走浏览器打印对话框的"另存为 PDF" —— 后端没有装任何 PDF 库
                    (reportlab/weasyprint/fpdf 全缺), 中文还要额外配 CID 字体,
                    跨平台风险高, 不如让浏览器做它最擅长的事。 */}
                <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>
                  预览打印
                </Button>
                <Button icon={<FilePdfOutlined />} onClick={() => setPrintOpen(true)}>
                  导出 PDF
                </Button>
                {detail.status === 'draft' && (
                  <>
                    <Button
                      icon={<EditOutlined />}
                      onClick={() => openEditModal(detail)}
                    >
                      编辑
                    </Button>
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      loading={submitting}
                      onClick={() => handleSubmit(detail.id)}
                    >
                      提交审批
                    </Button>
                  </>
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

      {/* C3 预览打印 / 导出 PDF: 还原纸质家访记录表 (§7.3) */}
      <Modal
        title="家访记录表 (打印预览)"
        open={printOpen}
        onCancel={() => setPrintOpen(false)}
        width={860}
        footer={[
          <Button key="close" onClick={() => setPrintOpen(false)}>
            关闭
          </Button>,
          <Button
            key="print"
            type="primary"
            icon={<PrinterOutlined />}
            onClick={() => window.print()}
          >
            打印 / 另存为 PDF
          </Button>,
        ]}
      >
        {detail && (
          <div className="home-visit-print">
            <style>{`
              /* 打印时只留记录表本体: Modal 的按钮/遮罩/滚动条都不该进纸面 */
              @media print {
                body * { visibility: hidden; }
                .home-visit-print, .home-visit-print * { visibility: visible; }
                .home-visit-print {
                  position: absolute; left: 0; top: 0; width: 100%;
                  padding: 0; margin: 0;
                }
                @page { size: A4; margin: 12mm; }
              }
            `}</style>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                {[
                  ['所属团队', detail.team_name || '审核处理团队'],
                  ['被家访人姓名', detail.visited_name || ''],
                  ['被家访人 EHR 号', detail.visited_ehr_id || ''],
                  ['岗位', detail.position || ''],
                  ['联系电话', detail.contact_phone || ''],
                  ['家访年度', String(detail.visit_year)],
                  ['家访时间', detail.visit_time],
                  ['家访方式', detail.visit_method],
                  ['家访地址', detail.visit_address || ''],
                  ['家访人员及岗位', detail.visitor_info || ''],
                  ['是否已家访', detail.is_visited ? '是' : '否'],
                  ['反馈意见', detail.feedback || ''],
                  ['家访记录表扫描件', detail.scan_status || '未提交'],
                ].map(([label, value]) => (
                  <tr key={label as string}>
                    <td
                      style={{
                        width: 160, border: '1px solid #999', padding: '6px 10px',
                        background: '#fafafa', fontWeight: 600, verticalAlign: 'top',
                      }}
                    >
                      {label}
                    </td>
                    <td style={{ border: '1px solid #999', padding: '6px 10px', whiteSpace: 'pre-wrap' }}>
                      {value || ''}
                    </td>
                  </tr>
                ))}
                <tr>
                  <td style={{ border: '1px solid #999', padding: '6px 10px', background: '#fafafa', fontWeight: 600 }}>
                    家访人签字
                  </td>
                  <td style={{ border: '1px solid #999', padding: '28px 10px' }} />
                </tr>
                <tr>
                  <td style={{ border: '1px solid #999', padding: '6px 10px', background: '#fafafa', fontWeight: 600 }}>
                    被家访人签字
                  </td>
                  <td style={{ border: '1px solid #999', padding: '28px 10px' }} />
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: 12, color: '#999', fontSize: 12 }}>
              打印对话框里选「另存为 PDF」即可导出 PDF 格式。
            </div>
          </div>
        )}
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

      {/* C1: 新建家访两步表单 */}
      {user && (
        <CreateHomeVisitModal
          open={createOpen}
          onCancel={() => setCreateOpen(false)}
          onSuccess={(record) => {
            setCreateOpen(false);
            message.success(`家访草稿已创建 (ID=${record.id})`);
            // 跳到草稿 tab
            setStatusFilter('draft');
            setPage(1);
            fetchList();
          }}
          visitedCandidates={teamMembers
            .filter((m) => m.team_id === user.teamId)
            .map((m) => ({ ehr_id: m.ehr_id, name: m.name }))}
          coVisitorCandidates={teamMembers
            .filter((m) => m.team_id === user.teamId)
            .map((m) => ({ id: m.id, name: m.name, ehr_id: m.ehr_id }))}
          currentUserId={user.id}
          // 从 teamMembers 列表中按 id 找当前用户的 ehr (兜底: username 排除)
          currentUserEhrId={
            teamMembers.find((m) => m.id === user.id)?.ehr_id || ''
          }
        />
      )}

      {/* Week 3 P0.3: 编辑家访草稿 (独立 modal 实例, 不动 create) */}
      {user && editingRecord && (
        <CreateHomeVisitModal
          mode="edit"
          visitId={editingRecord.id}
          initialValues={editingRecord}
          open={editModalOpen}
          onCancel={() => {
            setEditModalOpen(false);
            setEditingRecord(null);
          }}
          onSuccess={(record) => {
            setEditModalOpen(false);
            setEditingRecord(null);
            message.success(`家访草稿已更新 (ID=${record.id})`);
            fetchList();
            // 详情 Modal 还在, 刷新详情
            if (detail && detail.id === record.id) {
              PortraitAPI.getHomeVisit(record.id).then(setDetail).catch(() => {});
            }
          }}
          visitedCandidates={teamMembers
            .filter((m) => m.team_id === user.teamId)
            .map((m) => ({ ehr_id: m.ehr_id, name: m.name }))}
          coVisitorCandidates={teamMembers
            .filter((m) => m.team_id === user.teamId)
            .map((m) => ({ id: m.id, name: m.name, ehr_id: m.ehr_id }))}
          currentUserId={user.id}
          currentUserEhrId={
            teamMembers.find((m) => m.id === user.id)?.ehr_id || ''
          }
        />
      )}
    </div>
  );
};

export default HomeVisits;