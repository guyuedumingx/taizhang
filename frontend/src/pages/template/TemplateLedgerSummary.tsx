import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Table, 
  Button, 
  Space, 
  Input, 
  DatePicker, 
  message, 
  Breadcrumb, 
  Dropdown,
  MenuProps
} from 'antd';
import { 
  FileExcelOutlined, 
  FilePdfOutlined, 
  DownloadOutlined, 
  SearchOutlined, 
  EyeOutlined 
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { TemplateService } from '../../services/TemplateService';
import { LedgerService } from '../../services/LedgerService';
import { Ledger, Template } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';

// 初始化dayjs插件
dayjs.extend(isBetween);

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;

const TemplateLedgerSummary: React.FC = () => {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  const [template, setTemplate] = useState<Template | null>(null);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [searchText, setSearchText] = useState('');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  // 获取模板详情和相关台账
  useEffect(() => {
    const fetchTemplateAndLedgers = async () => {
      if (!templateId) return;
      
      setLoading(true);
      try {
        // 检查权限
        if (!hasPermission(PERMISSIONS.TEMPLATE_VIEW) || !hasPermission(PERMISSIONS.LEDGER_VIEW)) {
          message.error('您没有查看此页面的权限');
          navigate('/dashboard');
          return;
        }
        
        // 获取模板详情
        const templateData = await TemplateService.getTemplate(Number(templateId));
        setTemplate(templateData);
        
        // 获取该模板的所有台账
        const ledgerData = await LedgerService.getLedgersByTemplate(Number(templateId));
        setLedgers(ledgerData);
      } catch (error) {
        console.error('获取模板和台账数据失败:', error);
        message.error('获取数据失败');
      } finally {
        setLoading(false);
      }
    };
    
    fetchTemplateAndLedgers();
  }, [templateId, navigate, hasPermission]);

  // 处理搜索
  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  // 处理日期范围选择
  const handleDateChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    setDateRange(dates);
  };

  // 重置过滤器
  const handleReset = () => {
    setSearchText('');
    setDateRange(null);
  };

  // 处理导出
  const handleExport = async (format: string) => {
    if (!templateId) return;
    
    setExportLoading(true);
    try {
      const blob = await LedgerService.exportAllLedgers(format, Number(templateId));
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template?.name || '模板'}_台账汇总.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      message.success(`导出${format.toUpperCase()}成功`);
    } catch (error) {
      console.error('导出台账失败:', error);
      message.error('导出台账失败');
    } finally {
      setExportLoading(false);
    }
  };

  // 过滤台账数据
  const filteredLedgers = ledgers.filter(ledger => {
    // 文本搜索
    const textMatch = !searchText || 
      ledger.name.toLowerCase().includes(searchText.toLowerCase()) ||
      (ledger.description && ledger.description.toLowerCase().includes(searchText.toLowerCase())) ||
      (ledger.team_name && ledger.team_name.toLowerCase().includes(searchText.toLowerCase())) ||
      (ledger.created_by_name && ledger.created_by_name.toLowerCase().includes(searchText.toLowerCase()));
    
    // 日期过滤
    let dateMatch = true;
    if (dateRange && dateRange[0] && dateRange[1]) {
      const createdAt = dayjs(ledger.created_at);
      dateMatch = createdAt.isBetween(dateRange[0], dateRange[1], 'day', '[]');
    }
    
    return textMatch && dateMatch;
  });

  // 表格列定义
  const columns: ColumnsType<Ledger> = [
    {
      title: '台账名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text: string) => (
        <span style={{ color: text === '已完成' ? '#52c41a' : '#faad14' }}>
          {text}
        </span>
      ),
    },
    {
      title: '团队',
      dataIndex: 'team_name',
      key: 'team_name',
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/dashboard/ledgers/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.LEDGER_VIEW)}
          >
            查看
          </Button>
        </Space>
      ),
    },
  ];

  const items: MenuProps['items'] = [
    {
      key: 'excel',
      icon: <FileExcelOutlined />,
      label: '导出为Excel',
      onClick: () => handleExport('xlsx'),
    },
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: '导出为PDF',
      onClick: () => handleExport('pdf'),
    },
  ];

  return (
    <Card>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><a href="/dashboard">仪表盘</a></Breadcrumb.Item>
        <Breadcrumb.Item><a href="/dashboard/templates">模板管理</a></Breadcrumb.Item>
        <Breadcrumb.Item>{template?.name || '模板'} - 台账汇总</Breadcrumb.Item>
      </Breadcrumb>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>{template?.name || '模板'} - 台账汇总</Title>
        <Dropdown menu={{ items }} disabled={loading || ledgers.length === 0}>
          <Button type="primary" icon={<DownloadOutlined />} loading={exportLoading}>
            导出台账
          </Button>
        </Dropdown>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <Search
          placeholder="搜索台账"
          allowClear
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onSearch={handleSearch}
          style={{ width: 250 }}
        />
        <RangePicker
          value={dateRange}
          onChange={handleDateChange}
          placeholder={['开始日期', '结束日期']}
        />
        <Button 
          icon={<SearchOutlined />} 
          onClick={handleReset}
        >
          重置
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={filteredLedgers}
        rowKey="id"
        loading={loading}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
        locale={{
          emptyText: '没有找到相关台账数据',
        }}
      />
    </Card>
  );
};

export default TemplateLedgerSummary; 