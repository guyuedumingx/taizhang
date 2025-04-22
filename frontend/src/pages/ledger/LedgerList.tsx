import React, { useState, useEffect } from 'react';
import {
  Table,
  Input,
  Button,
  Space,
  Form,
  Row,
  Col,
  Select,
  DatePicker,
  message,
  Tag,
  Card,
  Typography,
  Popconfirm,
  Dropdown,
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  DownloadOutlined,
  DownOutlined,
  EyeOutlined,
  UpOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { LedgerService } from '../../services/LedgerService';
import { TemplateService } from '../../services/TemplateService';
import { TeamService } from '../../services/TeamService';
import { Ledger, Template, Team } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { exportLedgersViaAPI } from '../../utils/exportUtils';
import dayjs from 'dayjs';

const { Title } = Typography;
const { Search } = Input;

// 高级搜索条件接口
interface AdvancedSearchParams {
  name?: string;
  description?: string;
  team?: string;
  template?: string;
  status?: string;
  approvalStatus?: string;
  createdBy?: string;
  createdAtRange?: [dayjs.Dayjs, dayjs.Dayjs] | null;
}

const LedgerList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission, token, user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [searchText, setSearchText] = useState<string>('');
  
  // 高级搜索相关状态
  const [advancedSearchVisible, setAdvancedSearchVisible] = useState(true);
  const [advancedSearchForm] = Form.useForm();
  const [advancedSearchParams, setAdvancedSearchParams] = useState<AdvancedSearchParams>({
    name: '',
    description: '',
    team: undefined,
    template: undefined,
    status: undefined,
    approvalStatus: undefined,
    createdBy: '',
    createdAtRange: undefined
  });
  const [isAdvancedSearchActive, setIsAdvancedSearchActive] = useState<boolean>(false);

  // 获取台账列表和相关数据
  const fetchData = async () => {
    // 检查是否已登录
    if (!token) {
      navigate('/login');
      return;
    }
    
    setLoading(true);
    try {
      const [ledgersData, teamsData, templatesData] = await Promise.all([
        LedgerService.getLedgers(),
        TeamService.getTeams(),
        TemplateService.getTemplates()
      ]);
      setLedgers(ledgersData);
      setTeams(teamsData);
      setTemplates(templatesData);
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`获取数据失败: ${error.message}`);
      } else {
        message.error('获取数据失败');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token, navigate]);

  // 处理简单搜索
  const handleSearch = (value: string) => {
    setSearchText(value);
    // 如果开启了高级搜索，清除高级搜索条件
    if (isAdvancedSearchActive) {
      setIsAdvancedSearchActive(false);
      setAdvancedSearchParams({
        name: '',
        description: '',
        team: undefined,
        template: undefined,
        status: undefined,
        approvalStatus: undefined,
        createdBy: '',
        createdAtRange: undefined
      });
      advancedSearchForm.resetFields();
    }
  };

  // 处理高级搜索
  const handleAdvancedSearch = () => {
    const validParams = Object.entries(advancedSearchParams).filter(
      ([, value]) => value !== undefined && value !== '' && value !== null
    );

    if (validParams.length === 0) {
      setIsAdvancedSearchActive(false);
      return;
    }

    // 设置为活跃状态
    setIsAdvancedSearchActive(true);

    // 显示过滤后的结果
    setAdvancedSearchVisible(false);
  };

  // 重置高级搜索
  const resetAdvancedSearch = () => {
    advancedSearchForm.resetFields();
    setAdvancedSearchParams({
      name: '',
      description: '',
      team: undefined,
      template: undefined,
      status: undefined,
      approvalStatus: undefined,
      createdBy: '',
      createdAtRange: undefined
    });
    setIsAdvancedSearchActive(false);
  };

  // 删除台账
  const handleDelete = async (id: number) => {
    try {
      await LedgerService.deleteLedger(id);
      message.success('删除成功');
      fetchData();
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error(`删除失败: ${error.message}`);
      } else {
        message.error('删除失败');
      }
    }
  };

  // 处理导出单个台账
  const handleExport = async (id: number, format: string) => {
    try {
      message.loading({ content: '正在导出...', key: 'export' });
      const blob = await LedgerService.exportLedger(id, format);
      
      // 检查服务器返回的内容类型
      if (blob.type.includes('json')) {
        // 如果返回的是JSON（可能是错误信息），转换成文本并显示
        const text = await blob.text();
        const response = JSON.parse(text);
        message.error({ content: response.detail || '导出失败', key: 'export' });
        return;
      }
      
      // 根据格式确定文件扩展名
      let fileExtension = format;
      if (format.toLowerCase() === 'excel') {
        fileExtension = 'xlsx';
      }
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = `台账_${id}.${fileExtension}`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success({ content: '导出成功', key: 'export' });
    } catch (error: unknown) {
      if (error instanceof Error) {
        message.error({ content: `导出失败: ${error.message}`, key: 'export' });
      } else {
        message.error({ content: '导出失败', key: 'export' });
      }
    }
  };

  // 处理导出所有台账
  const handleExportAll = async (format: string) => {
    try {
      message.loading({ content: '正在导出...', key: 'exportAll' });
      await exportLedgersViaAPI(format);
      message.success({ content: '导出成功', key: 'exportAll' });
    } catch (error) {
      console.error('导出失败:', error);
      if (error instanceof Error) {
        message.error({ content: `导出失败: ${error.message}`, key: 'exportAll' });
      } else {
        message.error({ content: '导出失败', key: 'exportAll' });
      }
    }
  };

  // 过滤台账数据，支持简单搜索和高级搜索
  const filteredLedgers = ledgers.filter(item => {
    // 使用高级搜索条件筛选
    if (isAdvancedSearchActive) {
      const { 
        name, description, team, template, 
        status, approvalStatus, createdBy, createdAtRange 
      } = advancedSearchParams;

      // 名称匹配
      if (name && !item.name.toLowerCase().includes(name.toLowerCase())) {
        return false;
      }

      // 描述匹配
      if (description && (!item.description || !item.description.toLowerCase().includes(description.toLowerCase()))) {
        return false;
      }

      // 团队匹配
      if (team && item.team_id !== (typeof team === 'string' ? parseInt(team, 10) : team)) {
        return false;
      }

      // 模板匹配
      if (template && item.template_id !== (typeof template === 'string' ? parseInt(template, 10) : template)) {
        return false;
      }

      // 创建人匹配
      if (createdBy && (!item.created_by_name || !item.created_by_name.includes(createdBy))) {
        return false;
      }

      // 状态匹配
      if (status && item.status !== status) {
        return false;
      }

      // 审批状态匹配
      if (approvalStatus && item.approval_status !== approvalStatus) {
        return false;
      }

      // 创建时间范围匹配
      if (createdAtRange && Array.isArray(createdAtRange) && createdAtRange.length === 2 && item.created_at) {
        const itemDate = dayjs(item.created_at);
        if (!itemDate.isAfter(createdAtRange[0].startOf('day')) || !itemDate.isBefore(createdAtRange[1].endOf('day'))) {
          return false;
        }
      }

      return true;
    } else if (searchText) {
      // 简单搜索模式
      return (
        item.name.toLowerCase().includes(searchText.toLowerCase()) ||
        (item.description && item.description.toLowerCase().includes(searchText.toLowerCase())) ||
        (item.created_by_name && item.created_by_name.toLowerCase().includes(searchText.toLowerCase())) ||
        (item.team_name && item.team_name.toLowerCase().includes(searchText.toLowerCase())) ||
        (item.template_name && item.template_name.toLowerCase().includes(searchText.toLowerCase()))
      );
    }
    
    // 没有搜索条件则显示所有台账
    return true;
  });

  // 渲染高级搜索表单
  const renderAdvancedSearchForm = () => {
    return (
      <Form layout="vertical" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="名称">
              <Input
                placeholder="搜索台账名称"
                value={advancedSearchParams.name}
                onChange={(e) => setAdvancedSearchParams({ ...advancedSearchParams, name: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="描述">
              <Input
                placeholder="搜索台账描述"
                value={advancedSearchParams.description}
                onChange={(e) => setAdvancedSearchParams({ ...advancedSearchParams, description: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="创建人">
              <Input
                placeholder="搜索创建人"
                value={advancedSearchParams.createdBy}
                onChange={(e) => setAdvancedSearchParams({ ...advancedSearchParams, createdBy: e.target.value })}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="团队">
              <Select
                placeholder="选择团队"
                allowClear
                style={{ width: '100%' }}
                value={advancedSearchParams.team}
                onChange={(value) => setAdvancedSearchParams({ ...advancedSearchParams, team: value })}
              >
                {teams.map((team) => (
                  <Select.Option key={team.id} value={team.id}>
                    {team.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="模板">
              <Select
                placeholder="选择模板"
                allowClear
                style={{ width: '100%' }}
                value={advancedSearchParams.template}
                onChange={(value) => setAdvancedSearchParams({ ...advancedSearchParams, template: value })}
              >
                {templates.map((template) => (
                  <Select.Option key={template.id} value={template.id}>
                    {template.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="状态">
              <Select
                placeholder="选择状态"
                allowClear
                style={{ width: '100%' }}
                value={advancedSearchParams.status}
                onChange={(value) => setAdvancedSearchParams({ ...advancedSearchParams, status: value })}
              >
                <Select.Option value="active">活跃</Select.Option>
                <Select.Option value="inactive">非活跃</Select.Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="审批状态">
              <Select
                placeholder="选择审批状态"
                allowClear
                style={{ width: '100%' }}
                value={advancedSearchParams.approvalStatus}
                onChange={(value) => setAdvancedSearchParams({ ...advancedSearchParams, approvalStatus: value })}
              >
                <Select.Option value="approved">已批准</Select.Option>
                <Select.Option value="pending">审批中</Select.Option>
                <Select.Option value="rejected">已拒绝</Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="创建时间范围">
              <DatePicker.RangePicker
                style={{ width: '100%' }}
                value={advancedSearchParams.createdAtRange}
                onChange={(dates) => setAdvancedSearchParams({ ...advancedSearchParams, createdAtRange: dates as [dayjs.Dayjs, dayjs.Dayjs] | null })}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row>
          <Col span={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setAdvancedSearchParams({
                    name: '',
                    description: '',
                    team: undefined,
                    template: undefined,
                    status: undefined,
                    approvalStatus: undefined,
                    createdBy: '',
                    createdAtRange: undefined
                  });
                  setIsAdvancedSearchActive(false);
                }}
              >
                重置
              </Button>
              <Button type="primary" onClick={handleAdvancedSearch}>
                搜索
              </Button>
            </Space>
          </Col>
        </Row>
      </Form>
    );
  };

  // 渲染搜索标签，显示当前激活的高级搜索条件
  const renderSearchTags = () => {
    if (!isAdvancedSearchActive) return null;

    const tags = [];
    const params = advancedSearchParams;

    if (params.name) {
      tags.push(<Tag key="name" closable onClose={() => {
        advancedSearchForm.setFieldValue('name', undefined);
        handleAdvancedSearch();
      }}>台账名称: {params.name}</Tag>);
    }

    if (params.description) {
      tags.push(<Tag key="description" closable onClose={() => {
        advancedSearchForm.setFieldValue('description', undefined);
        handleAdvancedSearch();
      }}>描述: {params.description}</Tag>);
    }

    if (params.createdBy) {
      tags.push(<Tag key="createdBy" closable onClose={() => {
        advancedSearchForm.setFieldValue('createdBy', undefined);
        handleAdvancedSearch();
      }}>创建人: {params.createdBy}</Tag>);
    }

    if (params.template) {
      const templateId = typeof params.template === 'string' ? parseInt(params.template, 10) : params.template;
      const template = templates.find(t => t.id === templateId);
      tags.push(<Tag key="template" closable onClose={() => {
        advancedSearchForm.setFieldValue('template', undefined);
        handleAdvancedSearch();
      }}>模板: {template?.name || params.template}</Tag>);
    }

    if (params.team) {
      const teamId = typeof params.team === 'string' ? parseInt(params.team, 10) : params.team;
      const team = teams.find(t => t.id === teamId);
      tags.push(<Tag key="team" closable onClose={() => {
        advancedSearchForm.setFieldValue('team', undefined);
        handleAdvancedSearch();
      }}>团队: {team?.name || params.team}</Tag>);
    }

    if (params.status) {
      const statusText = {
        draft: '草稿',
        active: '处理中',
        completed: '已完成',
        returned: '已退回'
      }[params.status] || params.status;
      
      tags.push(<Tag key="status" closable onClose={() => {
        advancedSearchForm.setFieldValue('status', undefined);
        handleAdvancedSearch();
      }}>状态: {statusText}</Tag>);
    }

    if (params.approvalStatus) {
      const statusText = {
        draft: '草稿',
        pending: '审批中',
        approved: '已批准',
        rejected: '已拒绝'
      }[params.approvalStatus] || params.approvalStatus;
      
      tags.push(<Tag key="approvalStatus" closable onClose={() => {
        advancedSearchForm.setFieldValue('approvalStatus', undefined);
        handleAdvancedSearch();
      }}>审批状态: {statusText}</Tag>);
    }

    if (params.createdAtRange && params.createdAtRange.length === 2) {
      const startDate = params.createdAtRange[0].format('YYYY-MM-DD');
      const endDate = params.createdAtRange[1].format('YYYY-MM-DD');
      tags.push(<Tag key="createdAtRange" closable onClose={() => {
        advancedSearchForm.setFieldValue('createdAtRange', undefined);
        handleAdvancedSearch();
      }}>创建时间: {startDate} 至 {endDate}</Tag>);
    }

    if (tags.length > 0) {
      return (
        <div style={{ marginBottom: 16 }}>
          <Space size={[0, 8]} wrap>
            {tags}
            <Button type="link" size="small" onClick={resetAdvancedSearch}>清除所有筛选</Button>
          </Space>
        </div>
      );
    }

    return null;
  };

  const columns: ColumnsType<Ledger> = [
    {
      title: '台账名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      width: 180,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 200,
    },
    {
      title: '团队',
      dataIndex: 'team_name',
      key: 'team_name',
      width: 120,
      filters: teams
        .filter(team => team.name !== null)
        .map(team => ({ text: team.name || '', value: team.name || '' })),
      onFilter: (value, record) => record.team_name === value.toString(),
    },
    {
      title: '模板',
      dataIndex: 'template_name',
      key: 'template_name',
      width: 120,
      filters: templates
        .filter(template => template.name !== null)
        .map(template => ({ text: template.name || '', value: template.name || '' })),
      onFilter: (value, record) => record.template_name === value.toString(),
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
      width: 120,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a, b) => a.created_at.localeCompare(b.created_at),
      render: (text) => text ? new Date(text).toLocaleString() : '-',
      width: 180,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (text: string) => (
        <Tag color={text === 'completed' ? 'success' : text === 'active' ? 'processing' : text === 'returned' ? 'error' : 'default'}>
          {text === 'completed' ? '已完成' : text === 'active' ? '处理中' : text === 'returned' ? '已退回' : '草稿'}
        </Tag>
      ),
      filters: [
        { text: '草稿', value: 'draft' },
        { text: '处理中', value: 'active' },
        { text: '已完成', value: 'completed' },
        { text: '已退回', value: 'returned' },
      ],
      onFilter: (value, record) => record.status === value.toString(),
    },
    {
      title: '审批状态',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 130,
      render: (text: string) => (
        <Tag color={text === 'approved' ? 'success' : text === 'rejected' ? 'error' : text === 'pending' ? 'processing' : 'default'}>
          {text === 'approved' ? '已批准' : text === 'rejected' ? '已拒绝' : text === 'pending' ? '审批中' : '草稿'}
        </Tag>
      ),
      filters: [
        { text: '已批准', value: 'approved' },
        { text: '已拒绝', value: 'rejected' },
        { text: '审批中', value: 'pending' },
        { text: '草稿', value: 'draft' },
      ],
      onFilter: (value, record) => record.approval_status === value.toString(),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 220,
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/dashboard/ledgers/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/dashboard/ledgers/edit/${record.id}`)}
            // disabled={!hasPermission(PERMISSIONS.LEDGER_EDIT) || (record.approval_status !== 'draft' && record.approval_status !== 'rejected')}
            disabled={record.created_by_id !== user?.id || (record.approval_status !== 'draft' && record.approval_status !== 'rejected')}
          />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'excel',
                  label: 'Excel格式',
                  onClick: () => handleExport(record.id, 'excel')
                },
                {
                  key: 'csv',
                  label: 'CSV格式',
                  onClick: () => handleExport(record.id, 'csv')
                },
                {
                  key: 'txt',
                  label: 'TXT格式',
                  onClick: () => handleExport(record.id, 'txt')
                }
              ]
            }}
            disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT)}
          >
            <Button
              type="text"
              icon={<DownloadOutlined />}
              disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT)}
            />
          </Dropdown>
          <Popconfirm
            title="确定要删除这个台账吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.LEDGER_DELETE)}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.LEDGER_DELETE)}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '台账管理', path: '/dashboard/ledgers' }
        ]}
        showBackButton={false}
      />
      
      <div>
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Title level={4}>台账列表</Title>
            <Space>
              <Search
                placeholder="搜索台账名称/描述/模板/团队"
                allowClear
                onSearch={handleSearch}
                style={{ width: 300 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'excel',
                      label: '导出为Excel',
                      onClick: () => handleExportAll('excel')
                    },
                    {
                      key: 'csv',
                      label: '导出为CSV',
                      onClick: () => handleExportAll('csv')
                    },
                    {
                      key: 'txt',
                      label: '导出为TXT',
                      onClick: () => handleExportAll('txt')
                    }
                  ]
                }}
                disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT) || ledgers.length === 0}
              >
                <Button 
                  type="default" 
                  icon={<DownloadOutlined />}
                  disabled={!hasPermission(PERMISSIONS.LEDGER_EXPORT) || ledgers.length === 0}
                >
                  导出
                </Button>
              </Dropdown>
              {hasPermission(PERMISSIONS.LEDGER_CREATE) && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => navigate('/dashboard/ledgers/new')}
                >
                  新建台账
                </Button>
              )}
            </Space>
          </div>

          {/* 高级搜索表单 */}
          <div style={{ marginBottom: 16 }}>
            {advancedSearchVisible && renderAdvancedSearchForm()}
            <Button
              type="link"
              icon={advancedSearchVisible ? <UpOutlined /> : <DownOutlined />}
              onClick={() => setAdvancedSearchVisible(!advancedSearchVisible)}
              style={{ padding: 0 }}
            >
              {advancedSearchVisible ? '收起' : '展开'}高级筛选
            </Button>
          </div>

          {/* 显示激活的搜索条件 */}
          {renderSearchTags()}

          <Table
            columns={columns}
            dataSource={filteredLedgers}
            rowKey="id"
            loading={loading}
            pagination={{
              defaultPageSize: 10,
              showQuickJumper: true,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条记录`
            }}
            scroll={{ x: 1300 }}
          />
        </Card>
      </div>
    </>
  );
};

export default LedgerList; 