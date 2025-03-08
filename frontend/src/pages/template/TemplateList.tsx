import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Popconfirm, message, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Search } = Input;

interface TemplateItem {
  id: number;
  name: string;
  description: string;
  department: string;
  fieldCount: number;
  createdBy: string;
  createdAt: string;
  isSystem: boolean;
}

const TemplateList: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    // 模拟获取数据
    setTimeout(() => {
      const mockData: TemplateItem[] = [];
      for (let i = 1; i <= 10; i++) {
        mockData.push({
          id: i,
          name: `模板示例 ${i}`,
          description: `这是模板示例 ${i} 的描述`,
          department: i % 3 === 0 ? '财务部' : i % 3 === 1 ? '生产部' : '客服部',
          fieldCount: 5 + (i % 5),
          createdBy: i % 4 === 0 ? '张三' : i % 4 === 1 ? '李四' : i % 4 === 2 ? '王五' : '赵六',
          createdAt: `2023-${Math.floor(i / 3) + 1}-${(i % 28) + 1}`,
          isSystem: i <= 3, // 前3个是系统模板
        });
      }
      setTemplates(mockData);
      setLoading(false);
    }, 1000);
  }, []);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleDelete = (id: number) => {
    // 模拟删除操作
    setTemplates(templates.filter(item => item.id !== id));
    message.success('删除成功');
  };

  const handleDuplicate = (id: number) => {
    const template = templates.find(item => item.id === id);
    if (template) {
      const newTemplate: TemplateItem = {
        ...template,
        id: Math.max(...templates.map(t => t.id)) + 1,
        name: `${template.name} (复制)`,
        isSystem: false,
        createdAt: new Date().toISOString().split('T')[0],
      };
      setTemplates([...templates, newTemplate]);
      message.success('复制成功');
    }
  };

  const filteredTemplates = templates.filter(item => 
    item.name.toLowerCase().includes(searchText.toLowerCase()) ||
    item.description.toLowerCase().includes(searchText.toLowerCase()) ||
    item.department.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns: ColumnsType<TemplateItem> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: TemplateItem) => (
        <Space>
          {text}
          {record.isSystem && <Tag color="blue">系统</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      filters: [
        { text: '财务部', value: '财务部' },
        { text: '生产部', value: '生产部' },
        { text: '客服部', value: '客服部' },
      ],
      onFilter: (value, record) => record.department === value.toString(),
    },
    {
      title: '字段数量',
      dataIndex: 'fieldCount',
      key: 'fieldCount',
      sorter: (a, b) => a.fieldCount - b.fieldCount,
    },
    {
      title: '创建人',
      dataIndex: 'createdBy',
      key: 'createdBy',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      sorter: (a, b) => a.createdAt.localeCompare(b.createdAt),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => navigate(`/templates/edit/${record.id}`)}
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_EDIT) || record.isSystem}
            title={record.isSystem ? '系统模板不可编辑' : '编辑模板'}
          />
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={() => handleDuplicate(record.id)}
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_CREATE)}
            title="复制模板"
          />
          <Popconfirm
            title="确定要删除这个模板吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.TEMPLATE_DELETE) || record.isSystem}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.TEMPLATE_DELETE) || record.isSystem}
              title={record.isSystem ? '系统模板不可删除' : '删除模板'}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>模板列表</Title>
          <Space>
            <Search
              placeholder="搜索模板"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/templates/new')}
              disabled={!hasPermission(PERMISSIONS.TEMPLATE_CREATE)}
            >
              新建模板
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredTemplates}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>
    </div>
  );
};

export default TemplateList; 