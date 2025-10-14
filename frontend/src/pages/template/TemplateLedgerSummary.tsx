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
  Dropdown,
  MenuProps,
  Select,
  Row,
  Col,
  Drawer,
  Form,
  Checkbox,
  InputNumber,
  Divider,
  Tag,
  Tooltip,
} from 'antd';
import { 
  FileExcelOutlined, 
  DownloadOutlined, 
  EyeOutlined,
  FilterOutlined,
  ClearOutlined,
  DownOutlined,
  ColumnHeightOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { TemplateService } from '../../services/TemplateService';
import { LedgerService } from '../../services/LedgerService';
import { Ledger, Template, Field } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { exportLedgersViaAPI, exportTemplateAllLedgers } from '../../utils/exportUtils';

// 初始化dayjs插件
dayjs.extend(isBetween);

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;
const { Option } = Select;

// 定义高级搜索字段条件类型
interface AdvancedSearchConditions {
  [fieldName: string]: unknown;
}

const TemplateLedgerSummary: React.FC = () => {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  const [template, setTemplate] = useState<Template | null>(null);
  const [ledgers, setLedgers] = useState<Ledger[]>([]);
  const [templateFields, setTemplateFields] = useState<Field[]>([]);
  const [searchText, setSearchText] = useState('');
  const [searchField, setSearchField] = useState('name'); // 默认搜索台账名称
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [advancedSearchVisible, setAdvancedSearchVisible] = useState(false);
  const [advancedConditions, setAdvancedConditions] = useState<AdvancedSearchConditions>({});
  const [activeAdvancedSearch, setActiveAdvancedSearch] = useState(false);
  const [form] = Form.useForm();
  const [showAllFields, setShowAllFields] = useState(true);

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
        
        // 获取模板字段
        const fieldsData = await TemplateService.getTemplateFields(Number(templateId));
        setTemplateFields(fieldsData);
        
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

  // 处理字段选择变更
  const handleFieldChange = (value: string) => {
    setSearchField(value);
  };

  // 处理日期范围选择
  const handleDateChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    setDateRange(dates);
  };

  // 重置过滤器
  const handleReset = () => {
    setSearchText('');
    setDateRange(null);
    setSearchField('name');
    setAdvancedConditions({});
    setActiveAdvancedSearch(false);
    form.resetFields();
  };

  // 显示高级搜索抽屉
  const showAdvancedSearch = () => {
    setAdvancedSearchVisible(true);
  };

  // 关闭高级搜索抽屉
  const closeAdvancedSearch = () => {
    setAdvancedSearchVisible(false);
  };

  // 应用高级搜索
  const applyAdvancedSearch = async () => {
    try {
      const values = await form.validateFields();
      setAdvancedConditions(values);
      setActiveAdvancedSearch(true);
      closeAdvancedSearch();
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  // 处理导出
  const handleExport = async (format: string) => {
    if (!templateId) {
      message.error('模板ID不能为空');
      return;
    }
    
    setExportLoading(true);
    message.loading({ content: '正在准备导出...', key: 'export' });
    
    try {
      // 确保模板ID是有效整数
      const templateIdNumber = parseInt(templateId, 10);
      if (isNaN(templateIdNumber)) {
        message.error('模板ID必须是有效整数');
        setExportLoading(false);
        return;
      }
      
      // 使用新的导出工具函数
      if (format === 'excel') {
        // 使用客户端导出，支持多sheet
        await exportTemplateAllLedgers(templateIdNumber, `${template?.name || '模板'}_台账汇总.xlsx`);
        message.success({ content: '导出成功', key: 'export' });
      } else {
        // 使用API导出，支持CSV和TXT格式
        await exportLedgersViaAPI(format, templateIdNumber);
        message.success({ content: '导出成功', key: 'export' });
      }
    } catch (error) {
      console.error('导出失败:', error);
      message.error({ 
        content: error instanceof Error ? error.message : '导出失败，请稍后再试', 
        key: 'export' 
      });
    } finally {
      setExportLoading(false);
    }
  };

  // 生成可用字段列表
  const getFieldOptions = () => {
    // 系统默认字段
    const systemFields = [
      { value: 'name', label: '台账名称' },
      { value: 'description', label: '描述' },
      { value: 'status', label: '状态' },
      { value: 'team_name', label: '团队' },
      { value: 'created_by_name', label: '创建人' },
    ];
    
    // 结合系统字段和模板自定义字段
    return [
      ...systemFields,
      ...templateFields.map(field => ({ 
        value: field.name, 
        label: field.label
      }))
    ];
  };

  // 过滤台账数据
  const filteredLedgers = ledgers.filter(ledger => {
    // 文本搜索
    let textMatch = true;
    if (searchText) {
      if (searchField === 'name') {
        textMatch = ledger.name.toLowerCase().includes(searchText.toLowerCase());
      } else if (searchField === 'description') {
        textMatch = ledger.description ? ledger.description.toLowerCase().includes(searchText.toLowerCase()) : false;
      } else if (searchField === 'status') {
        textMatch = ledger.status.toLowerCase().includes(searchText.toLowerCase());
      } else if (searchField === 'team_name') {
        textMatch = ledger.team_name ? ledger.team_name.toLowerCase().includes(searchText.toLowerCase()) : false;
      } else if (searchField === 'created_by_name') {
        textMatch = ledger.created_by_name ? ledger.created_by_name.toLowerCase().includes(searchText.toLowerCase()) : false;
      } else {
        // 搜索自定义字段
        const fieldValue = ledger.data[searchField];
        textMatch = fieldValue ? String(fieldValue).toLowerCase().includes(searchText.toLowerCase()) : false;
      }
    }
    
    // 日期过滤
    let dateMatch = true;
    if (dateRange && dateRange[0] && dateRange[1]) {
      const createdAt = dayjs(ledger.created_at);
      dateMatch = createdAt.isBetween(dateRange[0], dateRange[1], 'day', '[]');
    }
    
    // 高级搜索过滤
    let advancedMatch = true;
    if (activeAdvancedSearch && Object.keys(advancedConditions).length > 0) {
      advancedMatch = Object.entries(advancedConditions).every(([field, value]) => {
        // 忽略未设置的值
        if (value === undefined || value === null || value === '') {
          return true;
        }
        
        // 系统字段
        if (field === 'name') {
          return ledger.name.toLowerCase().includes(String(value).toLowerCase());
        } else if (field === 'description') {
          return ledger.description ? ledger.description.toLowerCase().includes(String(value).toLowerCase()) : false;
        } else if (field === 'status') {
          return ledger.status === value;
        } else if (field === 'team_name') {
          return ledger.team_name === value;
        } else if (field === 'created_by_name') {
          return ledger.created_by_name === value;
        } else if (field === 'created_at_range') {
          if (Array.isArray(value) && value[0] && value[1]) {
            const createdAt = dayjs(ledger.created_at);
            return createdAt.isBetween(value[0], value[1], 'day', '[]');
          }
          return true;
        } else {
          // 自定义字段
          const fieldValue = ledger.data[field];
          if (fieldValue === undefined) return true;
          
          // 根据字段类型进行不同的比较
          const fieldDef = templateFields.find(f => f.name === field);
          if (!fieldDef) return true;
          
          if (fieldDef.type === 'select' || fieldDef.type === 'radio') {
            // 单选或下拉
            return String(fieldValue) === String(value);
          } else if (fieldDef.type === 'checkbox') {
            // 多选
            if (!Array.isArray(value)) return true;
            if (!Array.isArray(fieldValue)) {
              // 可能是字符串，尝试解析
              try {
                const parsedValue = JSON.parse(String(fieldValue));
                if (Array.isArray(parsedValue)) {
                  return value.every(v => parsedValue.includes(v));
                }
              } catch {
                // 解析失败，尝试直接比较
                return value.includes(String(fieldValue));
              }
            } else {
              return value.every(v => fieldValue.includes(v));
            }
          } else if (fieldDef.type === 'number') {
            // 数字
            const numFieldValue = Number(fieldValue);
            const numValue = value as Record<string, number>;
            const min = numValue.min !== undefined ? Number(numValue.min) : -Infinity;
            const max = numValue.max !== undefined ? Number(numValue.max) : Infinity;
            return !isNaN(numFieldValue) && numFieldValue >= min && numFieldValue <= max;
          } else if (fieldDef.type === 'date') {
            // 日期
            if (Array.isArray(value) && value[0] && value[1]) {
              const dateValue = dayjs(fieldValue as string | number | Date);
              return dateValue.isBetween(value[0], value[1], 'day', '[]');
            }
            return true;
          } else {
            // 文本类型，默认包含搜索
            return String(fieldValue).toLowerCase().includes(String(value).toLowerCase());
          }
        }
      });
    }
    
    return textMatch && dateMatch && advancedMatch;
  });

  // 根据字段类型渲染搜索控件
  const renderFieldSearchControl = (field: Field) => {
    switch (field.type) {
      case 'select':
      case 'radio':
        return (
          <Form.Item 
            label={field.label}
            name={field.name || ''}
          >
            <Select
              placeholder={`选择${field.label}`}
              allowClear
            >
              {field.options?.map((option, index) => (
                <Option key={index} value={option}>{option}</Option>
              ))}
            </Select>
          </Form.Item>
        );
      case 'checkbox':
        return (
          <Form.Item 
            label={field.label}
            name={field.name || ''}
          >
            <Checkbox.Group>
              {field.options?.map((option, index) => (
                <Checkbox key={index} value={option}>{option}</Checkbox>
              ))}
            </Checkbox.Group>
          </Form.Item>
        );
      case 'date':
        return (
          <Form.Item 
            label={field.label}
            name={field.name || ''}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
        );
      case 'number':
        return (
          <Form.Item 
            label={field.label}
            name={field.name || ''}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Form.Item 
                name={[field.name || '', 'min']} 
                noStyle
              >
                <InputNumber
                  placeholder="最小值"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item 
                name={[field.name || '', 'max']} 
                noStyle
              >
                <InputNumber
                  placeholder="最大值"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Space>
          </Form.Item>
        );
      default:
        return (
          <Form.Item 
            label={field.label}
            name={field.name || ''}
          >
            <Input placeholder={`搜索${field.label}`} />
          </Form.Item>
        );
    }
  };

  // 渲染系统字段搜索控件
  const renderSystemFieldControls = () => {
    return (
      <>
        <Form.Item
          label="台账名称"
          name="name"
        >
          <Input placeholder="搜索台账名称" />
        </Form.Item>
        <Form.Item
          label="描述"
          name="description"
        >
          <Input placeholder="搜索描述" />
        </Form.Item>
        <Form.Item
          label="状态"
          name="status"
        >
          <Select placeholder="选择状态" allowClear>
            <Option value="草稿">草稿</Option>
            <Option value="待审批">待审批</Option>
            <Option value="已完成">已完成</Option>
            <Option value="已拒绝">已拒绝</Option>
          </Select>
        </Form.Item>
        <Form.Item
          label="团队"
          name="team_name"
        >
          <Input placeholder="搜索团队" />
        </Form.Item>
        <Form.Item
          label="创建人"
          name="created_by_name"
        >
          <Input placeholder="搜索创建人" />
        </Form.Item>
        <Form.Item
          label="创建时间"
          name="created_at_range"
        >
          <RangePicker style={{ width: '100%' }} />
        </Form.Item>
      </>
    );
  };

  // 表格列定义
  const getColumns = () => {
    // 基础固定列
    const baseColumns: ColumnsType<Ledger> = [
      {
        title: '台账名称',
        dataIndex: 'name',
        key: 'name',
        sorter: (a, b) => a.name.localeCompare(b.name),
        fixed: 'left',
        width: 150,
      },
      {
        title: '描述',
        dataIndex: 'description',
        key: 'description',
        ellipsis: true,
        width: 200,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 100,
        render: (text: string) => (
          <span style={{ color: text === '已完成' ? '#52c41a' : '#faad14' }}>
            {text}
          </span>
        ),
      },
    ];

    // 自定义字段列
    const customColumns = showAllFields ? templateFields.map(field => ({
      title: field.label || field.name || '未命名字段',
      key: field.name || `field_${field.id}`,
      dataIndex: ['data', field.name || ''],
      width: 150,
      ellipsis: true,
      render: (value: any) => {
        // 根据字段类型渲染不同的显示方式
        if (field.type === 'checkbox' && Array.isArray(value)) {
          return value.join(', ');
        } else if (field.type === 'date' && value) {
          return dayjs(value).format('YYYY-MM-DD');
        } else if (value === null || value === undefined) {
          return '-';
        }
        return String(value);
      }
    })) : [];

    // 尾部固定列
    const endColumns: ColumnsType<Ledger> = [
      {
        title: '团队',
        dataIndex: 'team_name',
        key: 'team_name',
        width: 120,
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
        width: 180,
        sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        render: (text) => text ? new Date(text).toLocaleString() : '-',
      },
      {
        title: '操作',
        key: 'action',
        fixed: 'right',
        width: 100,
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

    return [...baseColumns, ...customColumns, ...endColumns];
  };

  const items: MenuProps['items'] = [
    {
      key: 'excel',
      icon: <FileExcelOutlined />,
      label: '导出为Excel',
      onClick: () => handleExport('excel'),
    },
    {
      key: 'csv',
      icon: <DownloadOutlined />,
      label: '导出为CSV',
      onClick: () => handleExport('csv'),
    },
    {
      key: 'txt',
      icon: <DownloadOutlined />,
      label: '导出为TXT',
      onClick: () => handleExport('txt'),
    },
  ];

  // 渲染高级搜索标签
  const renderActiveSearchTags = () => {
    if (!activeAdvancedSearch || Object.keys(advancedConditions).length === 0) {
      return null;
    }

    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8 }}>高级筛选条件:</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {Object.entries(advancedConditions).map(([field, value]) => {
            // 如果值为空，跳过
            if (value === undefined || value === null || value === '' || 
               (Array.isArray(value) && value.length === 0)) {
              return null;
            }

            // 获取字段标签
            let label = field;
            if (field === 'name') label = '台账名称';
            else if (field === 'description') label = '描述';
            else if (field === 'status') label = '状态';
            else if (field === 'team_name') label = '团队';
            else if (field === 'created_by_name') label = '创建人';
            else if (field === 'created_at_range') label = '创建时间';
            else {
              const fieldDef = templateFields.find(f => f.name === field);
              if (fieldDef) label = fieldDef.label || '';
            }

            // 根据字段类型格式化值
            let displayValue = '';
            if (field === 'created_at_range' && Array.isArray(value) && value[0] && value[1]) {
              displayValue = `${dayjs(value[0]).format('YYYY-MM-DD')} 至 ${dayjs(value[1]).format('YYYY-MM-DD')}`;
            } else if (Array.isArray(value)) {
              displayValue = value.join(', ');
            } else if (typeof value === 'object' && value !== null) {
              // 处理数字范围
              const numValue = value as Record<string, number>;
              const min = numValue.min;
              const max = numValue.max;
              if (min !== undefined && max !== undefined) {
                displayValue = `${min} 至 ${max}`;
              } else if (min !== undefined) {
                displayValue = `>= ${min}`;
              } else if (max !== undefined) {
                displayValue = `<= ${max}`;
              }
            } else {
              displayValue = String(value);
            }

            return (
              <Tag key={field} color="blue">
                {`${label}: ${displayValue}`}
              </Tag>
            );
          })}
          <Button 
            type="link" 
            size="small" 
            icon={<ClearOutlined />} 
            onClick={() => {
              setAdvancedConditions({});
              setActiveAdvancedSearch(false);
              form.resetFields();
            }}
          >
            清除筛选
          </Button>
        </div>
      </div>
    );
  };

  return (
    <Card>
      <BreadcrumbNav
        items={[
          { title: '模板管理', path: '/dashboard/templates' },
          { title: `${template?.name || '模板'} - 台账汇总` }
        ]}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>{template?.name || '模板'} - 台账汇总</Title>
        <Space>
          <Tooltip title={showAllFields ? "隐藏自定义字段" : "显示所有自定义字段"}>
            <Button 
              icon={<ColumnHeightOutlined />} 
              onClick={() => setShowAllFields(!showAllFields)}
              type={showAllFields ? "primary" : "default"}
            >
              {showAllFields ? "隐藏字段" : "显示所有字段"}
            </Button>
          </Tooltip>
          <Dropdown menu={{ items }} trigger={['click']} disabled={loading || ledgers.length === 0}>
            <Button type="primary" icon={<DownloadOutlined />} loading={exportLoading}>
              导出台账 <DownOutlined />
            </Button>
          </Dropdown>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} md={6}>
          <Select
            placeholder="选择搜索字段"
            style={{ width: '100%' }}
            value={searchField}
            onChange={handleFieldChange}
          >
            {getFieldOptions().map(option => (
              <Option key={option.value} value={option.value}>{option.label}</Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} md={8}>
          <Search
            placeholder={`搜索${getFieldOptions().find(o => o.value === searchField)?.label || '台账'}`}
            allowClear
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={handleSearch}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} md={6}>
          <RangePicker
            value={dateRange}
            onChange={handleDateChange}
            placeholder={['开始日期', '结束日期']}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} md={4}>
          <Space style={{ width: '100%' }}>
            <Button 
              type="primary" 
              icon={<FilterOutlined />} 
              onClick={showAdvancedSearch}
            >
              高级筛选
            </Button>
            <Button 
              icon={<ClearOutlined />} 
              onClick={handleReset}
            >
              重置
            </Button>
          </Space>
        </Col>
      </Row>

      {renderActiveSearchTags()}

      <Table
        columns={getColumns()}
        dataSource={filteredLedgers}
        rowKey="id"
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
        locale={{
          emptyText: '没有找到相关台账数据',
        }}
      />

      {/* 高级搜索抽屉 */}
      <Drawer
        title="高级搜索"
        width={500}
        placement="right"
        onClose={closeAdvancedSearch}
        open={advancedSearchVisible}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={closeAdvancedSearch}>取消</Button>
              <Button onClick={() => form.resetFields()}>清空</Button>
              <Button type="primary" onClick={applyAdvancedSearch}>
                应用筛选
              </Button>
            </Space>
          </div>
        }
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={advancedConditions}
        >
          <Divider>系统字段</Divider>
          {renderSystemFieldControls()}
          
          {templateFields.length > 0 && (
            <>
              <Divider>自定义字段</Divider>
              {templateFields.map(field => (
                <div key={field.id}>
                  {renderFieldSearchControl(field)}
                </div>
              ))}
            </>
          )}
        </Form>
      </Drawer>
    </Card>
  );
};

export default TemplateLedgerSummary; 