import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Modal, Form, message, Popconfirm, Checkbox, Divider } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Search } = Input;
const { Group: CheckboxGroup } = Checkbox;

interface Role {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  isSystem: boolean;
  createdAt: string;
}

interface PermissionGroup {
  groupName: string;
  permissions: {
    key: string;
    label: string;
  }[];
}

const RoleManagement: React.FC = () => {
  const { hasPermission } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [roles, setRoles] = useState<Role[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [form] = Form.useForm();

  // 检查权限
  useEffect(() => {
    if (!hasPermission(PERMISSIONS.ROLE_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    // 获取角色列表和权限列表
    setLoading(true);
    Promise.all([
      // 模拟获取角色列表
      new Promise<Role[]>(resolve => {
        setTimeout(() => {
          resolve([
            {
              id: 1,
              name: 'admin',
              description: '系统管理员',
              permissions: Object.values(PERMISSIONS),
              isSystem: true,
              createdAt: '2023-01-01',
            },
            {
              id: 2,
              name: 'manager',
              description: '部门经理',
              permissions: [
                PERMISSIONS.LEDGER_VIEW,
                PERMISSIONS.LEDGER_CREATE,
                PERMISSIONS.LEDGER_EDIT,
                PERMISSIONS.LEDGER_DELETE,
                PERMISSIONS.TEMPLATE_VIEW,
                PERMISSIONS.TEMPLATE_CREATE,
                PERMISSIONS.TEMPLATE_EDIT,
                PERMISSIONS.USER_VIEW,
              ],
              isSystem: true,
              createdAt: '2023-01-01',
            },
            {
              id: 3,
              name: 'user',
              description: '普通用户',
              permissions: [
                PERMISSIONS.LEDGER_VIEW,
                PERMISSIONS.LEDGER_CREATE,
                PERMISSIONS.LEDGER_EDIT,
                PERMISSIONS.TEMPLATE_VIEW,
              ],
              isSystem: true,
              createdAt: '2023-01-01',
            },
            {
              id: 4,
              name: 'guest',
              description: '访客',
              permissions: [
                PERMISSIONS.LEDGER_VIEW,
                PERMISSIONS.TEMPLATE_VIEW,
              ],
              isSystem: false,
              createdAt: '2023-02-15',
            },
          ]);
        }, 1000);
      }),
      // 模拟获取权限分组
      new Promise<PermissionGroup[]>(resolve => {
        setTimeout(() => {
          resolve([
            {
              groupName: '台账管理',
              permissions: [
                { key: PERMISSIONS.LEDGER_VIEW, label: '查看台账' },
                { key: PERMISSIONS.LEDGER_CREATE, label: '创建台账' },
                { key: PERMISSIONS.LEDGER_EDIT, label: '编辑台账' },
                { key: PERMISSIONS.LEDGER_DELETE, label: '删除台账' },
                { key: PERMISSIONS.LEDGER_EXPORT, label: '导出台账' },
              ],
            },
            {
              groupName: '模板管理',
              permissions: [
                { key: PERMISSIONS.TEMPLATE_VIEW, label: '查看模板' },
                { key: PERMISSIONS.TEMPLATE_CREATE, label: '创建模板' },
                { key: PERMISSIONS.TEMPLATE_EDIT, label: '编辑模板' },
                { key: PERMISSIONS.TEMPLATE_DELETE, label: '删除模板' },
              ],
            },
            {
              groupName: '用户管理',
              permissions: [
                { key: PERMISSIONS.USER_VIEW, label: '查看用户' },
                { key: PERMISSIONS.USER_CREATE, label: '创建用户' },
                { key: PERMISSIONS.USER_EDIT, label: '编辑用户' },
                { key: PERMISSIONS.USER_DELETE, label: '删除用户' },
              ],
            },
            {
              groupName: '角色管理',
              permissions: [
                { key: PERMISSIONS.ROLE_VIEW, label: '查看角色' },
                { key: PERMISSIONS.ROLE_CREATE, label: '创建角色' },
                { key: PERMISSIONS.ROLE_EDIT, label: '编辑角色' },
                { key: PERMISSIONS.ROLE_DELETE, label: '删除角色' },
              ],
            },
            {
              groupName: '团队管理',
              permissions: [
                { key: PERMISSIONS.TEAM_VIEW, label: '查看团队' },
                { key: PERMISSIONS.TEAM_CREATE, label: '创建团队' },
                { key: PERMISSIONS.TEAM_EDIT, label: '编辑团队' },
                { key: PERMISSIONS.TEAM_DELETE, label: '删除团队' },
              ],
            },
          ]);
        }, 500);
      }),
    ]).then(([rolesData, permissionGroupsData]) => {
      setRoles(rolesData);
      setPermissionGroups(permissionGroupsData);
      setLoading(false);
    });
  }, [hasPermission]);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const showAddModal = () => {
    form.resetFields();
    setModalTitle('添加角色');
    setEditingRoleId(null);
    setIsModalVisible(true);
  };

  const showEditModal = (role: Role) => {
    form.setFieldsValue({
      name: role.name,
      description: role.description,
      permissions: role.permissions,
    });
    setModalTitle('编辑角色');
    setEditingRoleId(role.id);
    setIsModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then(values => {
      if (editingRoleId) {
        // 编辑角色
        const updatedRoles = roles.map(role => {
          if (role.id === editingRoleId) {
            return {
              ...role,
              ...values,
            };
          }
          return role;
        });
        setRoles(updatedRoles);
        message.success('角色更新成功');
      } else {
        // 添加角色
        const newRole: Role = {
          id: Math.max(...roles.map(r => r.id)) + 1,
          name: values.name,
          description: values.description,
          permissions: values.permissions || [],
          isSystem: false,
          createdAt: new Date().toISOString().split('T')[0],
        };
        setRoles([...roles, newRole]);
        message.success('角色添加成功');
      }
      setIsModalVisible(false);
    });
  };

  const handleDelete = (id: number) => {
    setRoles(roles.filter(role => role.id !== id));
    message.success('角色删除成功');
  };

  const filteredRoles = roles.filter(role => 
    role.name.toLowerCase().includes(searchText.toLowerCase()) ||
    role.description.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns: ColumnsType<Role> = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '权限数量',
      key: 'permissionCount',
      render: (_, record) => record.permissions.length,
      sorter: (a, b) => a.permissions.length - b.permissions.length,
    },
    {
      title: '系统角色',
      dataIndex: 'isSystem',
      key: 'isSystem',
      render: (isSystem: boolean) => isSystem ? '是' : '否',
      filters: [
        { text: '是', value: true },
        { text: '否', value: false },
      ],
      onFilter: (value, record) => record.isSystem === value,
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
            disabled={!hasPermission(PERMISSIONS.ROLE_EDIT) || record.isSystem}
            title={record.isSystem ? '系统角色不可编辑' : '编辑角色'}
          />
          <Popconfirm
            title="确定要删除这个角色吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.ROLE_DELETE) || record.isSystem}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.ROLE_DELETE) || record.isSystem}
              title={record.isSystem ? '系统角色不可删除' : '删除角色'}
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
          { title: '系统管理', path: '/dashboard/admin' },
          { title: '角色管理', path: '/dashboard/admin/roles' }
        ]}
        showBackButton={false}
      />
      
      <div>
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Title level={4}>角色管理</Title>
            <Space>
              <Search
                placeholder="搜索角色"
                allowClear
                onSearch={handleSearch}
                style={{ width: 250 }}
              />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={showAddModal}
                disabled={!hasPermission(PERMISSIONS.ROLE_CREATE)}
              >
                添加角色
              </Button>
            </Space>
          </div>
          <Table
            columns={columns}
            dataSource={filteredRoles}
            rowKey="id"
            loading={loading}
            pagination={{
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
            }}
            expandable={{
              expandedRowRender: (record) => (
                <div style={{ margin: 0 }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 8 }}>权限列表：</div>
                  <div>
                    {permissionGroups.map(group => {
                      const groupPermissions = group.permissions.filter(p => 
                        record.permissions.includes(p.key)
                      );
                      
                      if (groupPermissions.length === 0) return null;
                      
                      return (
                        <div key={group.groupName} style={{ marginBottom: 8 }}>
                          <span style={{ fontWeight: 'bold' }}>{group.groupName}：</span>
                          {groupPermissions.map(p => p.label).join('、')}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ),
            }}
          />
        </Card>

        <Modal
          title={modalTitle}
          open={isModalVisible}
          onOk={handleModalOk}
          onCancel={() => setIsModalVisible(false)}
          width={700}
          destroyOnClose
        >
          <Form
            form={form}
            layout="vertical"
          >
            <Form.Item
              label="角色名称"
              name="name"
              rules={[
                { required: true, message: '请输入角色名称' },
                { min: 2, message: '角色名称至少2个字符' },
              ]}
            >
              <Input disabled={!!editingRoleId} />
            </Form.Item>
            
            <Form.Item
              label="描述"
              name="description"
              rules={[{ required: true, message: '请输入描述' }]}
            >
              <Input />
            </Form.Item>
            
            <Divider>权限设置</Divider>
            
            <Form.Item
              name="permissions"
            >
              <div>
                {permissionGroups.map(group => (
                  <div key={group.groupName} style={{ marginBottom: 16 }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8 }}>{group.groupName}</div>
                    <CheckboxGroup
                      options={group.permissions.map(p => ({ label: p.label, value: p.key }))}
                    />
                  </div>
                ))}
              </div>
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </>
  );
};

export default RoleManagement; 