import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Modal, Form, Select, message, Popconfirm, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

interface Team {
  id: number;
  name: string;
  department: string;
  description: string;
  leaderId: number | null;
  leaderName: string | null;
  memberCount: number;
  createdAt: string;
}

interface User {
  id: number;
  name: string;
  department: string;
}

const TeamManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [editingTeamId, setEditingTeamId] = useState<number | null>(null);
  const [form] = Form.useForm();

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.TEAM_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    // 获取团队列表和用户列表
    setLoading(true);
    Promise.all([
      // 模拟获取团队列表
      new Promise<Team[]>(resolve => {
        setTimeout(() => {
          const mockTeams: Team[] = [];
          for (let i = 1; i <= 10; i++) {
            mockTeams.push({
              id: i,
              name: `团队${i}`,
              department: i % 4 === 0 ? '财务部' : i % 4 === 1 ? '生产部' : i % 4 === 2 ? '客服部' : '设备部',
              description: `这是团队${i}的描述`,
              leaderId: i % 5 === 0 ? null : i,
              leaderName: i % 5 === 0 ? null : `用户${i}`,
              memberCount: 5 + (i % 10),
              createdAt: `2023-${Math.floor(i / 3) + 1}-${(i % 28) + 1}`,
            });
          }
          resolve(mockTeams);
        }, 1000);
      }),
      // 模拟获取用户列表
      new Promise<User[]>(resolve => {
        setTimeout(() => {
          const mockUsers: User[] = [];
          for (let i = 1; i <= 20; i++) {
            mockUsers.push({
              id: i,
              name: `用户${i}`,
              department: i % 4 === 0 ? '财务部' : i % 4 === 1 ? '生产部' : i % 4 === 2 ? '客服部' : '设备部',
            });
          }
          resolve(mockUsers);
        }, 500);
      }),
    ]).then(([teamsData, usersData]) => {
      setTeams(teamsData);
      setUsers(usersData);
      setLoading(false);
    });
  }, [hasPermission]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const showAddModal = () => {
    form.resetFields();
    setModalTitle('添加团队');
    setEditingTeamId(null);
    setIsModalVisible(true);
  };

  const showEditModal = (team: Team) => {
    form.setFieldsValue({
      name: team.name,
      department: team.department,
      description: team.description,
      leaderId: team.leaderId,
    });
    setModalTitle('编辑团队');
    setEditingTeamId(team.id);
    setIsModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then(values => {
      const leader = users.find(user => user.id === values.leaderId);
      
      if (editingTeamId) {
        // 编辑团队
        const updatedTeams = teams.map(team => {
          if (team.id === editingTeamId) {
            return {
              ...team,
              ...values,
              leaderName: leader ? leader.name : null,
            };
          }
          return team;
        });
        setTeams(updatedTeams);
        message.success('团队更新成功');
      } else {
        // 添加团队
        const newTeam: Team = {
          id: Math.max(...teams.map(t => t.id)) + 1,
          name: values.name,
          department: values.department,
          description: values.description,
          leaderId: values.leaderId,
          leaderName: leader ? leader.name : null,
          memberCount: 0,
          createdAt: new Date().toISOString().split('T')[0],
        };
        setTeams([...teams, newTeam]);
        message.success('团队添加成功');
      }
      setIsModalVisible(false);
    });
  };

  const handleDelete = (id: number) => {
    setTeams(teams.filter(team => team.id !== id));
    message.success('团队删除成功');
  };

  const filteredTeams = teams.filter(team => 
    team.name.toLowerCase().includes(searchText.toLowerCase()) ||
    team.department.toLowerCase().includes(searchText.toLowerCase()) ||
    team.description.toLowerCase().includes(searchText.toLowerCase()) ||
    (team.leaderName && team.leaderName.toLowerCase().includes(searchText.toLowerCase()))
  );

  const columns: ColumnsType<Team> = [
    {
      title: '团队名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      filters: [
        { text: '财务部', value: '财务部' },
        { text: '生产部', value: '生产部' },
        { text: '客服部', value: '客服部' },
        { text: '设备部', value: '设备部' },
      ],
      onFilter: (value, record) => record.department === value.toString(),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '团队负责人',
      dataIndex: 'leaderName',
      key: 'leaderName',
      render: (leaderName: string | null) => leaderName || <Tag color="warning">未指定</Tag>,
    },
    {
      title: '成员数量',
      dataIndex: 'memberCount',
      key: 'memberCount',
      sorter: (a, b) => a.memberCount - b.memberCount,
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
            icon={<UserOutlined />}
            onClick={() => navigate(`/admin/teams/${record.id}/members`)}
            disabled={!hasPermission(PERMISSIONS.TEAM_VIEW)}
            title="查看成员"
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
            disabled={!hasPermission(PERMISSIONS.TEAM_EDIT)}
          />
          <Popconfirm
            title="确定要删除这个团队吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.TEAM_DELETE)}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.TEAM_DELETE)}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 模拟导航函数
  const navigate = (path: string) => {
    console.log('导航到:', path);
    message.info(`功能开发中: ${path}`);
  };

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}>团队管理</Title>
          <Space>
            <Search
              placeholder="搜索团队"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showAddModal}
              disabled={!hasPermission(PERMISSIONS.TEAM_CREATE)}
            >
              添加团队
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredTeams}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      <Modal
        title={modalTitle}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="团队名称"
            name="name"
            rules={[{ required: true, message: '请输入团队名称' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="部门"
            name="department"
            rules={[{ required: true, message: '请选择部门' }]}
          >
            <Select placeholder="选择部门">
              <Option value="财务部">财务部</Option>
              <Option value="生产部">生产部</Option>
              <Option value="客服部">客服部</Option>
              <Option value="设备部">设备部</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入描述' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          
          <Form.Item
            label="团队负责人"
            name="leaderId"
          >
            <Select allowClear placeholder="选择负责人">
              {users
                .filter(user => !editingTeamId || user.department === form.getFieldValue('department'))
                .map(user => (
                  <Option key={user.id} value={user.id}>
                    {user.name} ({user.department})
                  </Option>
                ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TeamManagement; 