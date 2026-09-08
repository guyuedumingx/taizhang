import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, Card, Collapse, DatePicker, Input, InputNumber, Select, Space,
  Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  DownloadOutlined, ReloadOutlined, SearchOutlined, WarningOutlined,
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
  FieldFilterCondition, FieldQuality, LedgerQueryItem, QueryField,
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

interface FieldFilterState {
  operator: FieldFilterCondition['operator'];
  value?: any;
}

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

  // 结果
  const [result, setResult] = useState<LedgerQueryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [quality, setQuality] = useState<FieldQuality[]>([]);
  const [qualityTotal, setQualityTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });
  const [sortInfo, setSortInfo] = useState<{ sortBy: string; sortOrder: 'asc' | 'desc' }>({
    sortBy: 'created_at', sortOrder: 'desc',
  });

  useEffect(() => {
    Promise.all([getTemplates({ limit: 100 }), getTeams({ limit: 100 }), getUsers({ limit: 200 })])
      .then(([t, tm, u]) => { setTemplates(t); setTeams(tm); setUsers(u); })
      .catch(() => {});
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
    setResult([]);
    setTotal(0);
    setQuality([]);
    setQualityTotal(0);
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
        </Space>

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
    </div>
  );
};

export default LedgerQuery;
