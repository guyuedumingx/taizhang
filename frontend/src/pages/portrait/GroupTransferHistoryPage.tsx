/**
 * 数字画像-组员调换历史 (G7, PRD §11.4, Week 3 P0.5)
 *
 * 只读列表 + admin 纠错删除。**没有新增入口** —— 记录由 team_id 变更自动写入。
 *
 * 权限: admin 全员 / 组长本组相关 (后端按 team_id 过滤) / 其他 403
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Popconfirm,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  ReloadOutlined,
  SearchOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import * as PortraitAPI from '../../api/portrait';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { useAuthStore } from '../../stores/authStore';

const { Title, Text } = Typography;

const GroupTransferHistoryPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<PortraitAPI.GroupTransferRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filters, setFilters] = useState<{
    name?: string;
    ehr_id?: string;
    year?: number;
    is_current?: boolean;
  }>({});

  // 与 EntryExitPage / DrillsPage 同一惯例: 非订阅式读取登录态
  const isAdmin =
    useAuthStore.getState().user?.roles?.includes('admin') ||
    useAuthStore.getState().user?.permissions?.includes('*:*') ||
    false;

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await PortraitAPI.getGroupTransferRecords({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        name: filters.name || undefined,
        ehr_id: filters.ehr_id || undefined,
        year: filters.year,
        is_current: filters.is_current,
      });
      setRecords(resp.items);
      setTotal(resp.total);
    } catch (err: any) {
      message.error(`加载调换历史失败: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const handleDelete = async (id: number) => {
    try {
      await PortraitAPI.deleteGroupTransferRecord(id);
      message.success('已删除该条记录');
      fetchList();
    } catch (err: any) {
      message.error(`删除失败: ${err?.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div>
      <BreadcrumbNav
        items={[{ title: '数字画像', path: '/dashboard/portrait/profile' }, { title: '组员调换历史' }]}
      />
      <Card
        title={
          <Space>
            <SwapOutlined />
            <Title level={4} style={{ margin: 0 }}>组员调换历史 (G7)</Title>
            <Text type="secondary">PRD §11.4</Text>
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => fetchList()} loading={loading}>
            刷新
          </Button>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="本页只记录「从第一次调组开始」的变动, 不补录历史存量"
          description={
            <Text type="secondary" style={{ fontSize: 12 }}>
              所以: 某人进入第一个有记录的组之前待了多久, 这里查不到 ——
              不要用本页数据做「在组时长」统计。系统只记录组别发生变化的那一刻。
            </Text>
          }
        />

        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            placeholder="姓名搜索"
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 160 }}
            onChange={(e) => setFilters((f) => ({ ...f, name: e.target.value || undefined }))}
          />
          <Input
            placeholder="EHR号 (7位)"
            allowClear
            maxLength={7}
            style={{ width: 140 }}
            onChange={(e) => setFilters((f) => ({ ...f, ehr_id: e.target.value || undefined }))}
          />
          <InputNumber
            placeholder="调组年份"
            min={2000}
            max={2100}
            style={{ width: 130 }}
            onChange={(v) => setFilters((f) => ({ ...f, year: v ?? undefined }))}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 160 }}
            value={filters.is_current}
            onChange={(v) => setFilters((f) => ({ ...f, is_current: v }))}
            options={[
              { value: true, label: '当前仍在该组' },
              { value: false, label: '已离开该组' },
            ]}
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
            { title: '姓名', dataIndex: 'user_name', width: 100, render: (v) => v || '—' },
            { title: 'EHR号', dataIndex: 'ehr_no', width: 100 },
            {
              title: '组别变动',
              width: 240,
              render: (_v, r: PortraitAPI.GroupTransferRecord) => (
                <Space size={4}>
                  <Text type={r.from_team_id === null ? 'secondary' : undefined}>
                    {r.from_group || '未分组'}
                  </Text>
                  <Text type="secondary">→</Text>
                  <Text strong>{r.to_group}</Text>
                </Space>
              ),
            },
            { title: '调组时间', dataIndex: 'transfer_date', width: 150, render: (v) => v?.slice(0, 16) },
            {
              title: '离组时间',
              dataIndex: 'leave_date',
              width: 150,
              render: (v) => (v ? v.slice(0, 16) : '—'),
            },
            {
              title: '当前状态',
              dataIndex: 'is_current',
              width: 130,
              render: (v: boolean) =>
                v ? <Tag color="green">当前在组</Tag> : <Tag>已离开</Tag>,
            },
            { title: '操作人', dataIndex: 'operator_name', width: 110 },
            { title: '调组原因', dataIndex: 'reason', ellipsis: true, render: (v) => v || '—' },
            {
              title: '操作',
              width: 100,
              render: (_v, r: PortraitAPI.GroupTransferRecord) => {
                if (!isAdmin) return null;
                if (r.is_current) {
                  // 开区间记录是「此人在此组」的凭证, 后端也会拒绝删除 —— 这里提前说明
                  return (
                    <Tooltip title="当前在组的记录不能删除, 请先把他调回正确组别, 系统会自动关闭错误记录">
                      <Button size="small" danger icon={<DeleteOutlined />} disabled>
                        删除
                      </Button>
                    </Tooltip>
                  );
                }
                return (
                  <Popconfirm
                    title="确定删除这条调换记录?"
                    description="仅用于纠错, 删除后不可恢复"
                    onConfirm={() => handleDelete(r.id)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                  </Popconfirm>
                );
              },
            },
          ]}
          scroll={{ x: 1400 }}
        />
      </Card>
    </div>
  );
};

export default GroupTransferHistoryPage;
