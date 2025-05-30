import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Modal, Form, Checkbox, message, Popconfirm, Card, Space, Typography, Row, Col } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { PERMISSIONS } from '../../config';
import { checkPermission } from '../../utils/permission';
import { Role, RoleCreate, RoleUpdate } from '../../types';
import { RoleService } from '../../services/RoleService';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';
import { PermissionGroupSimple, getPermissionGroupsSimple } from '../../utils/PermissionGroups';

const { Title } = Typography;

const RoleManagement: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [roles, setRoles] = useState<Role[]>([]);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('添加角色');
  const [editingRoleId, setEditingRoleId] = useState<number | null>(null);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroupSimple[]>([]);
  const [form] = Form.useForm();

  const hasPermission = checkPermission([PERMISSIONS.ROLE_VIEW]);

  // 加载数据
  useEffect(() => {
    if (!hasPermission) {
      message.error('您没有权限访问此页面');
      return;
    }

    setLoading(true);
    
    // 获取权限分组
    const permGroups = getPermissionGroupsSimple();
    setPermissionGroups(permGroups);
    
    // 获取角色列表
    RoleService.getRoles()
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
        
        RoleService.updateRole(editingRoleId, roleUpdate)
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
        
        RoleService.createRole(roleCreate)
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
    RoleService.deleteRole(id)
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