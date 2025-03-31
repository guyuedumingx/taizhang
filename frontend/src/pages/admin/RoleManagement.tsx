import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Modal, Form, Checkbox, message, Popconfirm, Card, Space, Typography, Row, Col } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { PERMISSIONS } from '../../config';
import { checkPermission } from '../../utils/permission';
import { Role, RoleCreate, RoleUpdate } from '../../types';
import api from '../../api';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

// 权限分组类型
interface PermissionGroup {
  groupName: string;
  permissions: Array<{ key: string; label: string }>;
}

const { Title } = Typography;

const RoleManagement: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [roles, setRoles] = useState<Role[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('添加角色');
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [form] = Form.useForm();

  const hasPermission = checkPermission([PERMISSIONS.ROLE_VIEW]);

  // 获取所有权限并按组分类
  const getPermissionGroups = (): PermissionGroup[] => {
    return [
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
    ];
  };

  // 加载数据
  useEffect(() => {
    if (!hasPermission) {
      message.error('您没有权限访问此页面');
      return;
    }

    setLoading(true);
    
    // 获取权限分组
    const permGroups = getPermissionGroups();
    setPermissionGroups(permGroups);
    
    // 获取角色列表
    api.roles.getRoles()
      .then(data => {
        setRoles(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('获取角色列表失败:', err);
        message.error('获取角色列表失败');
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
      setLoading(true);
      
      if (editingRoleId) {
        // 编辑角色
        const roleUpdate: RoleUpdate = {
          name: values.name,
          description: values.description,
          permissions: values.permissions,
        };
        
        api.roles.updateRole(editingRoleId, roleUpdate)
          .then(updatedRole => {
            // 更新本地数据
            setRoles(roles.map(role => 
              role.id === editingRoleId ? updatedRole : role
            ));
            message.success('角色更新成功');
            setIsModalVisible(false);
            setLoading(false);
          })
          .catch(err => {
            console.error('更新角色失败:', err);
            message.error('更新角色失败: ' + (err.response?.data?.detail || err.message));
            setLoading(false);
          });
      } else {
        // 添加角色
        const roleCreate: RoleCreate = {
          name: values.name,
          description: values.description,
          is_system: false,
          permissions: values.permissions || [],
        };
        
        api.roles.createRole(roleCreate)
          .then(newRole => {
            setRoles([...roles, newRole]);
            message.success('角色添加成功');
            setIsModalVisible(false);
            setLoading(false);
          })
          .catch(err => {
            console.error('添加角色失败:', err);
            message.error('添加角色失败: ' + (err.response?.data?.detail || err.message));
            setLoading(false);
          });
      }
    });
  };

  const handleDelete = (id: number) => {
    setLoading(true);
    api.roles.deleteRole(id)
      .then(() => {
        setRoles(roles.filter(role => role.id !== id));
        message.success('角色删除成功');
        setLoading(false);
      })
      .catch(err => {
        console.error('删除角色失败:', err);
        message.error('删除角色失败: ' + (err.response?.data?.detail || err.message));
        setLoading(false);
      });
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
      dataIndex: 'is_system',
      key: 'is_system',
      render: (isSystem) => isSystem ? '是' : '否',
      sorter: (a, b) => (a.is_system === b.is_system ? 0 : a.is_system ? 1 : -1),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
            disabled={!checkPermission([PERMISSIONS.ROLE_EDIT]) || record.is_system}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此角色吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!checkPermission([PERMISSIONS.ROLE_DELETE]) || record.is_system}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!checkPermission([PERMISSIONS.ROLE_DELETE]) || record.is_system}
            >
              删除
            </Button>
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
    <Card>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4}>角色管理</Title>
        </Col>
        <Col>
          <Space>
            <Input
              placeholder="搜索角色名称或描述"
              prefix={<SearchOutlined />}
              onChange={(e) => handleSearch(e.target.value)}
              style={{ width: 250 }}
              allowClear
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showAddModal}
              disabled={!checkPermission([PERMISSIONS.ROLE_CREATE])}
            >
              新建角色
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={filteredRoles}
        rowKey="id"
        loading={loading}
        pagination={{ showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
      />

      <Modal
        title={modalTitle}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
        width={800}
        maskClosable={false}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item
            name="description"
            label="角色描述"
            rules={[{ required: true, message: '请输入角色描述' }]}
          >
            <Input.TextArea placeholder="请输入角色描述" rows={4} />
          </Form.Item>
          <Form.Item
            name="permissions"
            label="权限设置"
            rules={[{ required: true, message: '请至少选择一个权限' }]}
            valuePropName="value"
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <div style={{ maxHeight: '350px', overflowY: 'auto', padding: '10px', border: '1px solid #d9d9d9', borderRadius: '4px', width: '100%' }}>
                {permissionGroups.map((group) => (
                  <div key={group.groupName} style={{ marginBottom: '15px', width: '100%' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>{group.groupName}</div>
                    <Row style={{ width: '100%' }}>
                      {group.permissions.map((permission) => (
                        <Col span={8} key={permission.key} style={{ marginBottom: '8px' }}>
                          <Checkbox value={permission.key}>{permission.label}</Checkbox>
                        </Col>
                      ))}
                    </Row>
                  </div>
                ))}
              </div>
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
    </>
  );
};

export default RoleManagement; 