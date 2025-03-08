import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Tag, Modal, Form, Select, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LockOutlined, UnlockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

interface User {
  id: number;
  username: string;
  name: string;
  email: string;
  role: string;
  department: string;
  teamId: number | null;
  teamName: string | null;
  status: 'active' | 'inactive';
  createdAt: string;
}

interface Team {
  id: number;
  name: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
}

const UserManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [form] = Form.useForm();

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.USER_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    // 获取用户列表
    setLoading(true);
    Promise.all([
      // 模拟获取用户列表
      new Promise<User[]>(resolve => {
        setTimeout(() => {
          const mockUsers: User[] = [];
          for (let i = 1; i <= 20; i++) {
            mockUsers.push({
              id: i,
              username: `user${i}`,
              name: `用户${i}`,
              email: `user${i}@example.com`,
              role: i === 1 ? 'admin' : i % 3 === 0 ? 'manager' : 'user',
              department: i % 4 === 0 ? '财务部' : i % 4 === 1 ? '生产部' : i % 4 === 2 ? '客服部' : '设备部',
              teamId: i === 1 ? null : (i % 4) + 1,
              teamName: i === 1 ? null : `团队${(i % 4) + 1}`,
              status: i % 7 === 0 ? 'inactive' : 'active',
              createdAt: `2023-${Math.floor(i / 3) + 1}-${(i % 28) + 1}`,
            });
          }
          resolve(mockUsers);
        }, 1000);
      }),
      // 模拟获取团队列表
      new Promise<Team[]>(resolve => {
        setTimeout(() => {
          resolve([
            { id: 1, name: '财务团队' },
            { id: 2, name: '生产团队' },
            { id: 3, name: '客服团队' },
            { id: 4, name: '设备团队' },
          ]);
        }, 500);
      }),
      // 模拟获取角色列表
      new Promise<Role[]>(resolve => {
        setTimeout(() => {
          resolve([
            { id: 1, name: 'admin', description: '系统管理员' },
            { id: 2, name: 'manager', description: '部门经理' },
            { id: 3, name: 'user', description: '普通用户' },
          ]);
        }, 500);
      }),
    ]).then(([usersData, teamsData, rolesData]) => {
      setUsers(usersData);
      setTeams(teamsData);
      setRoles(rolesData);
      setLoading(false);
    });
  }, [hasPermission]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const showAddModal = () => {
    form.resetFields();
    setModalTitle('添加用户');
    setEditingUserId(null);
    setIsModalVisible(true);
  };

  const showEditModal = (user: User) => {
    form.setFieldsValue({
      username: user.username,
      name: user.name,
      email: user.email,
      role: user.role,
      department: user.department,
      teamId: user.teamId,
      status: user.status,
    });
    setModalTitle('编辑用户');
    setEditingUserId(user.id);
    setIsModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then(values => {
      if (editingUserId) {
        // 编辑用户
        const updatedUsers = users.map(user => {
          if (user.id === editingUserId) {
            const teamObj = teams.find(team => team.id === values.teamId);
            return {
              ...user,
              ...values,
              teamName: teamObj ? teamObj.name : null,
            };
          }
          return user;
        });
        setUsers(updatedUsers);
        message.success('用户更新成功');
      } else {
        // 添加用户
        const newUser: User = {
          id: Math.max(...users.map(u => u.id)) + 1,
          username: values.username,
          name: values.name,
          email: values.email,
          role: values.role,
          department: values.department,
          teamId: values.teamId,
          teamName: values.teamId ? teams.find(team => team.id === values.teamId)?.name || null : null,
          status: values.status as 'active' | 'inactive',
          createdAt: new Date().toISOString().split('T')[0],
        };
        setUsers([...users, newUser]);
        message.success('用户添加成功');
      }
      setIsModalVisible(false);
    });
  };

  const handleDelete = (id: number) => {
    setUsers(users.filter(user => user.id !== id));
    message.success('用户删除成功');
  };

  const handleToggleStatus = (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    const updatedUsers = users.map(u => {
      if (u.id === user.id) {
        return { ...u, status: newStatus };
      }
      return u;
    });
    setUsers(updatedUsers);
    message.success(`用户${newStatus === 'active' ? '启用' : '禁用'}成功`);
  };

  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchText.toLowerCase()) ||
    user.name.toLowerCase().includes(searchText.toLowerCase()) ||
    user.email.toLowerCase().includes(searchText.toLowerCase()) ||
    (user.teamName && user.teamName.toLowerCase().includes(searchText.toLowerCase()))
  );

  const columns: ColumnsType<User> = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      sorter: (a, b) => a.username.localeCompare(b.username),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const colorMap: Record<string, string> = {
          admin: 'red',
          manager: 'blue',
          user: 'green',
        };
        return <Tag color={colorMap[role] || 'default'}>{role}</Tag>;
      },
      filters: roles.map(role => ({ text: role.description, value: role.name })),
      onFilter: (value, record) => record.role === value,
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
      title: '团队',
      dataIndex: 'teamName',
      key: 'teamName',
      render: (teamName: string | null) => teamName || '-',
      filters: teams.map(team => ({ text: team.name, value: team.name })),
      onFilter: (value, record) => record.teamName === value,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: 'active' | 'inactive') => (
        <Tag color={status === 'active' ? 'success' : 'error'}>
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
      filters: [
        { text: '启用', value: 'active' },
        { text: '禁用', value: 'inactive' },
      ],
      onFilter: (value, record) => record.status === value,
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
            onClick={() => showEditModal(record)}
            disabled={!hasPermission(PERMISSIONS.USER_EDIT)}
          />
          <Button
            type="text"
            icon={record.status === 'active' ? <LockOutlined /> : <UnlockOutlined />}
            onClick={() => handleToggleStatus(record)}
            disabled={!hasPermission(PERMISSIONS.USER_EDIT)}
          />
          <Popconfirm
            title="确定要删除这个用户吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.USER_DELETE) || record.role === 'admin'}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.USER_DELETE) || record.role === 'admin'}
              title={record.role === 'admin' ? '管理员用户不可删除' : '删除用户'}
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
          <Title level={4}>用户管理</Title>
          <Space>
            <Search
              placeholder="搜索用户"
              allowClear
              onSearch={handleSearch}
              style={{ width: 250 }}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showAddModal}
              disabled={!hasPermission(PERMISSIONS.USER_CREATE)}
            >
              添加用户
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={filteredUsers}
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
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
            ]}
          >
            <Input disabled={!!editingUserId} />
          </Form.Item>
          
          {!editingUserId && (
            <Form.Item
              label="密码"
              name="password"
              rules={[
                { required: !editingUserId, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password />
            </Form.Item>
          )}
          
          <Form.Item
            label="姓名"
            name="name"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select>
              {roles.map(role => (
                <Option key={role.name} value={role.name}>{role.description}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="部门"
            name="department"
            rules={[{ required: true, message: '请选择部门' }]}
          >
            <Select>
              <Option value="财务部">财务部</Option>
              <Option value="生产部">生产部</Option>
              <Option value="客服部">客服部</Option>
              <Option value="设备部">设备部</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="团队"
            name="teamId"
          >
            <Select allowClear placeholder="选择团队">
              {teams.map(team => (
                <Option key={team.id} value={team.id}>{team.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            label="状态"
            name="status"
            initialValue="active"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Option value="active">启用</Option>
              <Option value="inactive">禁用</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagement; 