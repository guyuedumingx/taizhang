import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, Card, Collapse, DatePicker, Empty, Input, InputNumber, List, message, Modal, Select, Space,
  Statistic, Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  DeleteOutlined, DownloadOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, SearchOutlined, SettingOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import dayjs from 'dayjs';

import { exportLedgerQuery, getQueryFields, ledgerQuery } from '../../api/statistics';
import { getTemplates } from '../../api/templates';
import { getTeams } from '../../api/teams';
import { getUsers } from '../../api/users';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type {
  AggregationResult, AggregationSpec, FieldFilterCondition, FieldQuality, LedgerQueryItem, QueryField,
  StatisticsQueryRequest, SuspiciousItem,
} from '../../types';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '活跃' },
  { value: 'completed', label: '已完成' },
];
const APPROVAL_OPTIONS = [
  { value: 'pending', label: '审批中' },
  { value: 'approved', label: '已批准' },
  { value: 'rejected', label: '已拒绝' },
];

const STATUS_LABELS: Record<string, string> = { draft: '草稿', active: '活跃', completed: '已完成' };
const APPROVAL_LABELS: Record<string, string> = { pending: '审批中', approved: '已批准', rejected: '已拒绝' };

const METRIC_OPTIONS = [
  { value: 'sum', label: '求和' },
  { value: 'count', label: '有效计数' },
  { value: 'avg', label: '平均' },
  { value: 'max', label: '最大' },
  { value: 'min', label: '最小' },
  { value: 'row_count', label: '台账条数' },
] as const;

interface FieldFilterState {
  operator: FieldFilterCondition['operator'];
  value?: any;
}

// ---------- 视图管理（localStorage 个人级持久化，零后端改动） ----------

const VIEWS_STORAGE_KEY = 'taizhang_ledger_query_views';

interface SavedView {
  name: string;
  saved_at: string;
  filters: {
    selectedTemplateIds: number[];
    keyword: string;
    statusSel: string[];
    approvalSel: string[];
    teamIds: number[];
    creatorIds: number[];
    createdAtRange: [string, string] | null;
    fieldFilters: Record<string, FieldFilterState>;
    aggregations: AggregationSpec[];
  };
}

const loadSavedViews = (): SavedView[] => {
  try {
    const raw = localStorage.getItem(VIEWS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const persistSavedViews = (views: SavedView[]) => {
  localStorage.setItem(VIEWS_STORAGE_KEY, JSON.stringify(views));
};

const LedgerQuery: React.FC = () => {
  const { hasPermission } = useAuthStore();

  // 基础数据
  const [templates, setTemplates] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);

  // 筛选条件
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<number[]>([]);
  const [keyword, setKeyword] = useState('');
  const [statusSel, setStatusSel] = useState<string[]>([]);
  const [approvalSel, setApprovalSel] = useState<string[]>([]);
  const [teamIds, setTeamIds] = useState<number[]>([]);
  const [creatorIds, setCreatorIds] = useState<number[]>([]);
  const [createdAtRange, setCreatedAtRange] = useState<any>(null);
  const [queryFields, setQueryFields] = useState<QueryField[]>([]);
  const [fieldFilters, setFieldFilters] = useState<Record<string, FieldFilterState>>({});

  // 动态统计指标
  const [aggregations, setAggregations] = useState<AggregationSpec[]>([]);

  // 结果
  const [result, setResult] = useState<LedgerQueryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [quality, setQuality] = useState<FieldQuality[]>([]);
  const [qualityTotal, setQualityTotal] = useState(0);
  const [aggResults, setAggResults] = useState<AggregationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });
  const [sortInfo, setSortInfo] = useState<{ sortBy: string; sortOrder: 'asc' | 'desc' }>({
    sortBy: 'created_at', sortOrder: 'desc',
  });

  // 视图管理状态
  const [savedViews, setSavedViews] = useState<SavedView[]>(loadSavedViews);
  const [saveViewOpen, setSaveViewOpen] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [manageViewsOpen, setManageViewsOpen] = useState(false);

  useEffect(() => {
    // 团队/用户接口返回分页对象 {items:[...]}，模板接口返回数组——统一归一化；
    // 用 allSettled 独立加载，单个接口失败只缺对应筛选数据，不拖垮整个页面
    const asArray = <T,>(v: T[] | { items?: T[] } | undefined): T[] => {
      if (Array.isArray(v)) return v;
      const items = (v as { items?: T[] } | undefined)?.items;
      return Array.isArray(items) ? items : [];
    };
    Promise.allSettled([getTemplates({ limit: 100 }), getTeams({ limit: 100 }), getUsers({ limit: 200 })])
      .then(([t, tm, u]) => {
        if (t.status === "fulfilled") setTemplates(asArray(t.value));
        if (tm.status === "fulfilled") setTeams(asArray(tm.value));
        if (u.status === "fulfilled") setUsers(asArray(u.value));
      });
  }, []);

  // 选中单个模板时加载其字段（动态筛选）
  useEffect(() => {
    if (selectedTemplateIds.length === 1) {
      getQueryFields(selectedTemplateIds[0])
        .then(setQueryFields)
        .catch(() => setQueryFields([]));
    } else {
      setQueryFields([]);
      setFieldFilters({});
    }
  }, [selectedTemplateIds]);

  const buildRequest = (
    page: number,
    pageSize: number,
    sortBy = sortInfo.sortBy,
    sortOrder = sortInfo.sortOrder,
  ): StatisticsQueryRequest => {
    const field_filters: Record<string, FieldFilterCondition> = {};
    Object.entries(fieldFilters).forEach(([name, st]) => {
      if (st.value === undefined || st.value === null || st.value === '' ||
          (Array.isArray(st.value) && (st.value as any[]).every((v) => v === undefined || v === null || v === ''))) {
        return;
      }
      field_filters[name] = { operator: st.operator, value: st.value };
    });
    return {
      template_ids: selectedTemplateIds,
      system_filters: {
        status: statusSel,
        approval_status: approvalSel,
        team_ids: teamIds,
        created_by_ids: creatorIds,
        created_at_range: createdAtRange?.[0]
          ? [
              createdAtRange[0].format('YYYY-MM-DD'),
              createdAtRange[1]?.format('YYYY-MM-DD') || createdAtRange[0].format('YYYY-MM-DD'),
            ]
          : null,
        updated_at_range: null,
      },
      field_filters,
      // 未选完字段的指标不提交（row_count 无需字段）
      aggregations: aggregations.filter((a) => a.type === 'row_count' || !!a.field),
      keyword: keyword.trim(),
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    };
  };

  const handleQuery = (page = 1, pageSize = pagination.pageSize) => {
    setLoading(true);
    ledgerQuery(buildRequest(page, pageSize))
      .then((resp) => {
        setResult(resp.items);
        setTotal(resp.total);
        setQuality(resp.data_quality.fields);
        setQualityTotal(resp.data_quality.total_count);
        setAggResults(resp.aggregations || []);
        setPagination({ page: resp.page, pageSize: resp.page_size });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const handleReset = () => {
    setSelectedTemplateIds([]);
    setKeyword('');
    setStatusSel([]);
    setApprovalSel([]);
    setTeamIds([]);
    setCreatorIds([]);
    setCreatedAtRange(null);
    setFieldFilters({});
    setQueryFields([]);
    setAggregations([]);
    setResult([]);
    setTotal(0);
    setQuality([]);
    setQualityTotal(0);
    setAggResults([]);
  };

  // ---------- 视图管理 ----------

  const captureFilters = (): SavedView['filters'] => ({
    selectedTemplateIds,
    keyword,
    statusSel,
    approvalSel,
    teamIds,
    creatorIds,
    createdAtRange: createdAtRange?.[0]
      ? [
          createdAtRange[0].format('YYYY-MM-DD'),
          createdAtRange[1]?.format('YYYY-MM-DD') || createdAtRange[0].format('YYYY-MM-DD'),
        ]
      : null,
    fieldFilters,
    aggregations,
  });

  const handleSaveView = () => {
    const name = newViewName.trim();
    if (!name) {
      message.warning('请输入视图名称');
      return;
    }
    const view: SavedView = { name, saved_at: dayjs().format('YYYY-MM-DD HH:mm'), filters: captureFilters() };
    const next = [...savedViews.filter((v) => v.name !== name), view];
    setSavedViews(next);
    persistSavedViews(next);
    setSaveViewOpen(false);
    setNewViewName('');
    message.success(`视图「${name}」已保存（仅保存在本浏览器）`);
  };

  const applyView = (view: SavedView) => {
    const f = view.filters;
    setSelectedTemplateIds(f.selectedTemplateIds || []);
    setKeyword(f.keyword || '');
    setStatusSel(f.statusSel || []);
    setApprovalSel(f.approvalSel || []);
    setTeamIds(f.teamIds || []);
    setCreatorIds(f.creatorIds || []);
    setCreatedAtRange(
      f.createdAtRange?.[0] ? [dayjs(f.createdAtRange[0]), dayjs(f.createdAtRange[1] || f.createdAtRange[0])] : null,
    );
    setFieldFilters(f.fieldFilters || {});
    setAggregations(f.aggregations || []);
    message.info(`已加载视图「${view.name}」，点击查询执行`);
  };

  const handleDeleteView = (name: string) => {
    const next = savedViews.filter((v) => v.name !== name);
    setSavedViews(next);
    persistSavedViews(next);
  };

  const handleTableChange = (
    pag: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<LedgerQueryItem> | SorterResult<LedgerQueryItem>[],
  ) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const sortBy = (s?.field as string) || 'created_at';
    const sortOrder = s?.order === 'ascend' ? 'asc' : 'desc';
    setSortInfo({ sortBy, sortOrder });
    setLoading(true);
    ledgerQuery(buildRequest(pag.current || 1, pag.pageSize || 20, sortBy, sortOrder))
      .then((resp) => {
        setResult(resp.items);
        setTotal(resp.total);
        setQuality(resp.data_quality.fields);
        setQualityTotal(resp.data_quality.total_count);
        setAggResults(resp.aggregations || []);
        setPagination({ page: resp.page, pageSize: resp.page_size });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportLedgerQuery(buildRequest(1, pagination.pageSize));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `台账汇总查询_${dayjs().format('YYYYMMDDHHmm')}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // 导出失败静默（由拦截器统一提示）
    } finally {
      setExporting(false);
    }
  };

  // 动态字段筛选控件
  const renderFieldControl = (f: QueryField) => {
    const st = fieldFilters[f.name] || { operator: 'contains' as const };
    const update = (patch: Partial<FieldFilterState>) =>
      setFieldFilters((prev) => ({ ...prev, [f.name]: { ...st, ...patch } }));

    if (f.has_pipeline) {
      // 配置了清洗规则的数值栏位：范围筛选（走清洗后值）
      return (
        <Space>
          <InputNumber placeholder="最小值" value={st.value?.[0]}
            onChange={(v) => update({ operator: 'between', value: [v, st.value?.[1]] })} />
          <span>~</span>
          <InputNumber placeholder="最大值" value={st.value?.[1]}
            onChange={(v) => update({ operator: 'between', value: [st.value?.[0], v] })} />
          {f.has_pipeline && <Tag color="blue">清洗栏位</Tag>}
        </Space>
      );
    }
    if (f.type === 'select' && f.options) {
      return (
        <Select
          allowClear placeholder="全部" style={{ minWidth: 140 }} value={st.value}
          options={f.options.map((o) => ({ value: o, label: o }))}
          onChange={(v) => update({ operator: 'equals', value: v })}
        />
      );
    }
    if (f.type === 'date') {
      return (
        <RangePicker
          value={st.value?.[0] ? [dayjs(st.value[0]), dayjs(st.value[1] || st.value[0])] : null}
          onChange={(_, strs) => update({
            operator: 'between',
            value: strs?.[0] ? [strs[0], strs[1] || strs[0]] : undefined,
          })}
        />
      );
    }
    return (
      <Input
        allowClear placeholder="包含…" value={st.value}
        onChange={(e) => update({ operator: 'contains', value: e.target.value })}
      />
    );
  };

  // 表格列：系统列 + 单模板时的字段列
  const columns: ColumnsType<LedgerQueryItem> = useMemo(() => {
    const systemCols: ColumnsType<LedgerQueryItem> = [
      { title: 'ID', dataIndex: 'id', key: 'id', width: 70, sorter: true },
      { title: '台账名称', dataIndex: 'name', key: 'name', width: 160, sorter: true, ellipsis: true },
      { title: '模板', dataIndex: 'template_name', key: 'template_name', width: 130, ellipsis: true },
      {
        title: '状态', dataIndex: 'status', key: 'status', width: 90,
        render: (v) => STATUS_LABELS[v] || v,
      },
      {
        title: '审批状态', dataIndex: 'approval_status', key: 'approval_status', width: 90,
        render: (v) => APPROVAL_LABELS[v] || v,
      },
      { title: '团队', dataIndex: 'team_name', key: 'team_name', width: 110, ellipsis: true },
      { title: '创建人', dataIndex: 'created_by_name', key: 'created_by_name', width: 100 },
      {
        title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 150, sorter: true,
        render: (v) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-'),
      },
    ];
    if (selectedTemplateIds.length === 1) {
      const fieldCols: ColumnsType<LedgerQueryItem> = queryFields.map((f) => ({
        title: f.label,
        dataIndex: ['data', f.name],
        key: f.name,
        width: 140,
        sorter: true,
        ellipsis: true,
        render: (_, record) => {
          const v = record.data?.[f.name];
          if (v === null || v === undefined || v === '') return '-';
          return String(v);
        },
      }));
      return [...systemCols, ...fieldCols];
    }
    return systemCols;
  }, [queryFields, selectedTemplateIds]);

  const hasSuspicious = quality.some((q) => q.suspicious_count > 0);

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="台账汇总查询"
        extra={
          <Button
            type="primary" icon={<DownloadOutlined />} loading={exporting}
            disabled={!hasPermission(PERMISSIONS.STATISTICS_VIEW) || total === 0}
            onClick={handleExport}
          >
            导出Excel
          </Button>
        }
      >
        {/* 筛选区 */}
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space wrap>
            <Select
              mode="multiple" allowClear placeholder="模板（不选=全部）" style={{ minWidth: 260 }}
              value={selectedTemplateIds}
              options={templates.map((t) => ({ value: t.id, label: t.name }))}
              onChange={setSelectedTemplateIds}
            />
            <Input
              allowClear placeholder="关键词（名称/描述）" style={{ width: 220 }} prefix={<SearchOutlined />}
              value={keyword} onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={() => handleQuery(1)}
            />
            <Select
              mode="multiple" allowClear placeholder="状态" style={{ minWidth: 120 }} maxTagCount="responsive"
              value={statusSel} options={STATUS_OPTIONS} onChange={setStatusSel}
            />
            <Select
              mode="multiple" allowClear placeholder="审批状态" style={{ minWidth: 120 }} maxTagCount="responsive"
              value={approvalSel} options={APPROVAL_OPTIONS} onChange={setApprovalSel}
            />
            <Select
              mode="multiple" allowClear placeholder="团队" style={{ minWidth: 130 }} maxTagCount="responsive"
              value={teamIds} options={teams.map((t) => ({ value: t.id, label: t.name }))} onChange={setTeamIds}
            />
            <Select
              mode="multiple" allowClear placeholder="创建人" style={{ minWidth: 130 }} maxTagCount="responsive"
              value={creatorIds}
              options={users.map((u) => ({ value: u.id, label: u.name || u.username }))}
              onChange={setCreatorIds}
            />
            <RangePicker value={createdAtRange} onChange={setCreatedAtRange} placeholder={['创建开始', '创建结束']} />
            <Select
              placeholder="加载视图" style={{ minWidth: 130 }} allowClear value={null}
              options={savedViews.map((v) => ({ value: v.name, label: v.name }))}
              onChange={(name) => {
                const v = savedViews.find((x) => x.name === name);
                if (v) applyView(v);
              }}
            />
            <Button icon={<SaveOutlined />} onClick={() => setSaveViewOpen(true)}>保存视图</Button>
            <Button icon={<SettingOutlined />} disabled={savedViews.length === 0}
                    onClick={() => setManageViewsOpen(true)} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={() => handleQuery(1)}>
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          </Space>

          {/* 单模板时的字段级筛选 */}
          {selectedTemplateIds.length === 1 && queryFields.length > 0 && (
            <Collapse
              items={[{
                key: 'fields',
                label: '字段筛选（当前模板）',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {queryFields.map((f) => (
                      <Space key={f.name} wrap>
                        <Text type="secondary" style={{ display: 'inline-block', width: 100 }}>
                          {f.label}{f.required ? ' *' : ''}
                        </Text>
                        {renderFieldControl(f)}
                      </Space>
                    ))}
                  </Space>
                ),
              }]}
            />
          )}

          {/* 动态统计指标 */}
          <div>
            <Space wrap align="center">
              <Text type="secondary" style={{ display: 'inline-block', width: 100 }}>统计指标</Text>
              {aggregations.map((a, i) => (
                <Space key={i} wrap>
                  <Select
                    style={{ width: 120 }}
                    value={a.type}
                    options={METRIC_OPTIONS.map((m) => ({ value: m.value, label: m.label }))}
                    onChange={(t) => setAggregations((prev) =>
                      prev.map((x, xi) => (xi === i ? { ...x, type: t, field: t === 'row_count' ? null : x.field } : x)),
                    )}
                  />
                  {a.type !== 'row_count' && (
                    <Select
                      placeholder="选择字段" style={{ width: 150 }}
                      value={a.field || undefined}
                      options={queryFields.filter((f) => f.has_pipeline).map((f) => ({ value: f.name, label: f.label }))}
                      onChange={(v) => setAggregations((prev) => prev.map((x, xi) => (xi === i ? { ...x, field: v } : x)))}
                    />
                  )}
                  <Button type="text" danger size="small" icon={<DeleteOutlined />}
                          onClick={() => setAggregations((prev) => prev.filter((_, xi) => xi !== i))} />
                </Space>
              ))}
              <Button size="small" icon={<PlusOutlined />}
                      onClick={() => setAggregations((prev) => [...prev, { type: 'sum', field: undefined }])}>
                添加指标
              </Button>
              <Tooltip title="求和/计数/平均/最大/最小只支持配置了清洗规则的字段；外币等可疑值自动排除。">
                <Text type="secondary" style={{ fontSize: 12 }}>ⓘ</Text>
              </Tooltip>
            </Space>
          </div>
        </Space>

        {/* 动态指标结果 */}
        {aggResults.length > 0 && (
          <Space wrap size={40} style={{ marginTop: 16 }}>
            {aggResults.map((a, i) => (
              <Statistic
                key={`${a.type}-${a.field}-${i}`}
                title={a.label || a.type}
                value={a.value === null ? '-' : a.value}
                precision={a.value !== null && !Number.isInteger(a.value) ? 2 : 0}
                suffix={a.type !== 'row_count' && a.value !== null ? '' : '条'}
              />
            ))}
          </Space>
        )}

        {/* 数据质量报告 */}
        {quality.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {hasSuspicious && (
              <Alert
                type="warning" showIcon icon={<WarningOutlined />}
                message="部分数据清洗后仍无法解析，已从聚合中排除"
                style={{ marginBottom: 8 }}
              />
            )}
            <Collapse
              items={quality.map((q) => ({
                key: q.field_name,
                label: (
                  <Space wrap>
                    <Text strong>{q.field_name}</Text>
                    <Text>汇总: {q.sum !== null ? q.sum.toLocaleString() : '-'}</Text>
                    <Text type="secondary">有效 {q.numeric_count} 条</Text>
                    {q.cleaned_count > 0 && <Tag color="blue">自动清洗 {q.cleaned_count} 条</Tag>}
                    {q.suspicious_count > 0 && <Tag color="orange">可疑 {q.suspicious_count} 条</Tag>}
                  </Space>
                ),
                children:
                  q.suspicious_items.length > 0 ? (
                    <Table<SuspiciousItem>
                      size="small" rowKey={(r) => `${r.ledger_id}-${r.field}-${r.raw}`}
                      dataSource={q.suspicious_items}
                      columns={[
                        { title: '台账ID', dataIndex: 'ledger_id', width: 80 },
                        { title: '台账名称', dataIndex: 'ledger_name', ellipsis: true },
                        { title: '字段', dataIndex: 'field', width: 100 },
                        {
                          title: '原始值', dataIndex: 'raw', width: 180,
                          render: (v) => <Tooltip title={v}><Text type="warning">{v}</Text></Tooltip>,
                        },
                        { title: '原因', dataIndex: 'reason', ellipsis: true },
                      ]}
                      pagination={{ pageSize: 5, hideOnSinglePage: true }}
                    />
                  ) : (
                    <Text type="secondary">该字段数据全部可正常解析。</Text>
                  ),
              }))}
            />
          </div>
        )}

        {/* 结果表 */}
        <Table<LedgerQueryItem>
          style={{ marginTop: 16 }}
          rowKey="id"
          size="middle"
          loading={loading}
          columns={columns}
          dataSource={result}
          onChange={handleTableChange}
          pagination={{
            current: pagination.page,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </Card>

      {/* 保存视图 */}
      <Modal
        open={saveViewOpen}
        title="保存当前筛选条件为视图"
        onCancel={() => setSaveViewOpen(false)}
        onOk={handleSaveView}
        okText="保存"
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="视图名称，例如: 本月大额台账"
            value={newViewName}
            onChange={(e) => setNewViewName(e.target.value)}
            onPressEnter={handleSaveView}
          />
          <Text type="secondary">视图保存在当前浏览器（localStorage），换设备或清理浏览器数据后不可恢复。</Text>
        </Space>
      </Modal>

      {/* 管理视图 */}
      <Modal
        open={manageViewsOpen}
        title="管理已保存视图"
        footer={null}
        onCancel={() => setManageViewsOpen(false)}
      >
        {savedViews.length === 0 ? (
          <Empty description="暂无视图" />
        ) : (
          <List
            size="small"
            dataSource={savedViews}
            renderItem={(v) => (
              <List.Item
                actions={[
                  <Button key="load" size="small" type="link" onClick={() => {
                    applyView(v);
                    setManageViewsOpen(false);
                  }}>载入</Button>,
                  <Button key="del" size="small" type="link" danger
                          onClick={() => handleDeleteView(v.name)}>删除</Button>,
                ]}
              >
                <List.Item.Meta
                  title={v.name}
                  description={`保存于 ${v.saved_at} · 模板 ${v.filters.selectedTemplateIds.length || '全部'}`}
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </div>
  );
};

export default LedgerQuery;
