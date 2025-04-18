import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Card, Typography, Tag, Modal, Form, Select, message, Popconfirm, Row, Col, Upload } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LockOutlined, UnlockOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import { PERMISSIONS } from '../../config';
import { UserService } from '../../services/UserService';
import { TeamService } from '../../services/TeamService';
import { RoleService } from '../../services/RoleService';
import { User, Team, Role, UserCreate, UserUpdate } from '../../types';
import useDepartments from '../../hooks/useDepartments';
import type { ColumnsType } from 'antd/es/table';
import BreadcrumbNav from '../../components/common/BreadcrumbNav';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;

interface ImportResult {
  success_count: number;
  failed_count: number;
  failed_users: Array<{
    row: number;
    username: string;
    reason: string;
  }>;
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
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const { options: departmentOptions, filters: departmentFilters } = useDepartments();

  // 获取数据
  const fetchData = async () => {
    if (!hasPermission(PERMISSIONS.USER_VIEW)) {
      message.error('您没有权限访问此页面');
      return;
    }

    setLoading(true);
    try {
      const [usersData, teamsData, rolesData] = await Promise.all([
        UserService.getUsers(),
        TeamService.getTeams(),
        RoleService.getRoles()
      ]);
      
      setUsers(usersData);
      setTeams(teamsData);
      setRoles(rolesData);
    } catch (error) {
      console.error('获取数据失败:', error);
      message.error('获取数据失败，请刷新页面重试');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载数据
  useEffect(() => {
    fetchData();
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
      ehr_id: user.ehr_id,
      department: user.department,
      team_id: user.team_id,
      is_active: user.is_active,
      roles: user.roles,
    });
    setModalTitle('编辑用户');
    setEditingUserId(user.id);
    setIsModalVisible(true);
  };

  // 处理模态框确认 - 修复后的版本，确保调用API
  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingUserId) {
        // 编辑用户 - 调用后端API
        const updateData: UserUpdate = {
          username: values.username,
          name: values.name,
          ehr_id: values.ehr_id,
          department: values.department,
          team_id: values.team_id,
          is_active: values.is_active,
          roles: values.roles,
        };
        
        // 如果提供了密码，添加到更新数据中
        if (values.password) {
          updateData.password = values.password;
        }
        
        await UserService.updateUser(editingUserId, updateData);
        message.success('用户更新成功');
        
        // 重新获取用户列表，确保数据同步
        fetchData();
      } else {
        // 添加用户 - 调用后端API
        const createData: UserCreate = {
          username: values.username,
          password: values.password, // 创建时密码是必需的
          name: values.name,
          ehr_id: values.ehr_id,
          department: values.department,
          team_id: values.team_id,
          is_active: values.is_active,
          roles: values.roles,
        };
        
        await UserService.createUser(createData);
        message.success('用户添加成功');
        
        // 重新获取用户列表，确保数据同步
        fetchData();
      }
      setIsModalVisible(false);
    } catch (error) {
      console.error('操作用户失败:', error);
      message.error('操作失败，请检查输入并重试');
    }
  };

  // 处理删除用户 - 修复后的版本，确保调用API
  const handleDelete = async (id: number) => {
    try {
      // 调用后端API删除用户
      await UserService.deleteUser(id);
      message.success('用户删除成功');
      
      // 重新获取用户列表，确保数据同步
      fetchData();
    } catch (error) {
      console.error('删除用户失败:', error);
      message.error('删除用户失败，请重试');
    }
  };

  // 处理用户状态切换 - 修复后的版本，确保调用API
  const handleToggleStatus = async (user: User) => {
    try {
      const newStatus = !user.is_active;
      
      // 调用后端API更新用户状态
      await UserService.updateUser(user.id, { 
        is_active: newStatus 
      });
      
      message.success(`用户${newStatus ? '启用' : '禁用'}成功`);
      
      // 重新获取用户列表，确保数据同步
      fetchData();
    } catch (error) {
      console.error('更新用户状态失败:', error);
      message.error('操作失败，请重试');
    }
  };

  const filteredUsers = users.filter(user => 
    user.username?.toLowerCase().includes(searchText.toLowerCase()) ||
    user.name?.toLowerCase().includes(searchText.toLowerCase()) ||
    user.ehr_id?.toLowerCase().includes(searchText.toLowerCase()) ||
    (user.team_name && user.team_name.toLowerCase().includes(searchText.toLowerCase()))
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
      title: 'EHR ID',
      dataIndex: 'ehr_id',
      key: 'ehr_id',
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[] | undefined) => roles ? (
        <Space direction="horizontal" size={[0, 4]} wrap>
          {roles.map(role => (
            <Tag key={role} color={role === 'admin' ? 'red' : role === 'manager' ? 'orange' : 'default'}>
              {role}
            </Tag>
          ))}
        </Space>
      ) : <span>-</span>,
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      filters: departmentFilters,
      onFilter: (value, record) => record.department === value.toString(),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (is_active: boolean) => (
        <Tag color={is_active ? 'green' : 'red'}>
          {is_active ? '启用' : '停用'}
        </Tag>
      ),
      filters: [
        { text: '启用', value: true },
        { text: '停用', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
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
            icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
            onClick={() => handleToggleStatus(record)}
            disabled={!hasPermission(PERMISSIONS.USER_EDIT)}
          />
          <Popconfirm
            title="确定要删除这个用户吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            disabled={!hasPermission(PERMISSIONS.USER_DELETE) || record.roles?.includes('admin')}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              disabled={!hasPermission(PERMISSIONS.USER_DELETE) || record.roles?.includes('admin')}
              title={record.roles?.includes('admin') ? '管理员用户不可删除' : '删除用户'}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 添加导入用户的方法
  const handleImportUsers = async (options: any) => {
    const { file, onSuccess, onError } = options;
    
    setImportLoading(true);
    
    try {
      const result = await UserService.importUsers(file);
      
      setImportResult(result);
      onSuccess?.(result, file);
      message.success(`成功导入 ${result.success_count} 个用户`);
      
      // 如果有失败的用户，显示警告
      if (result.failed_count > 0) {
        message.warning(`${result.failed_count} 个用户导入失败`);
      }
      
      // 刷新用户列表
      fetchData();
    } catch (error) {
      console.error('导入用户失败:', error);
      message.error('导入用户失败: ' + (error as Error).message);
      onError?.(error);
    } finally {
      setImportLoading(false);
    }
  };
  
  // 下载导入模板
  const handleDownloadTemplate = () => {
    // 创建一个包含标题行的CSV内容
    const csvContent = 'username,ehr_id,password,name,department,role,team_id\n' +
                      'user1,1234567,password123,用户1,技术部,user,1\n' +
                      'user2,7654321,password123,用户2,市场部,user,2';
    
    // 创建Blob对象
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // 创建下载链接
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.href = url;
    link.setAttribute('download', '用户导入模板.csv');
    document.body.appendChild(link);
    link.click();
    
    // 清理
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <BreadcrumbNav 
        items={[
          { title: '系统管理', path: '/dashboard/admin' },
          { title: '用户管理', path: '/dashboard/admin/users' }
        ]}
        showBackButton={false}
      />
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Title level={4}>用户列表</Title>
            <Space>
              <Search
                placeholder="搜索用户"
                allowClear
                onSearch={handleSearch}
                style={{ width: 250 }}
              />
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
              disabled={!hasPermission(PERMISSIONS.USER_CREATE)}
            >
              批量导入
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showAddModal}
              disabled={!hasPermission(PERMISSIONS.USER_CREATE)}
            >
              创建用户
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
            
            {editingUserId && (
              <Form.Item
                label="密码"
                name="password"
                extra="如不修改密码，请留空"
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
              label="EHR号"
              name="ehr_id"
              rules={[
                { required: true, message: '请输入EHR号' },
                { min: 7, max: 7, message: 'EHR号必须是7位数字' },
                { pattern: /^\d{7}$/, message: 'EHR号必须是7位数字' }
              ]}
            >
              <Input />
            </Form.Item>
            
            <Form.Item
              label="角色"
              name="roles"
              rules={[{ required: true, message: '请选择角色' }]}
            >
              <Select mode="multiple">
                {roles.map(role => (
                  <Option key={role.name} value={role.name}>{role.name} - {role.description}</Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="部门"
              name="department"
              rules={[{ required: true, message: '请选择部门' }]}
            >
              <Select>
                {departmentOptions.map((option) => (
                  <Option key={option.value} value={option.value}>{option.label}</Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="团队"
              name="team_id"
            >
              <Select allowClear placeholder="选择团队">
                {teams.map(team => (
                  <Option key={team.id} value={team.id}>{team.name}</Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="状态"
              name="is_active"
              initialValue={true}
              rules={[{ required: true, message: '请选择状态' }]}
            >
              <Select>
                <Option value={true}>启用</Option>
                <Option value={false}>禁用</Option>
              </Select>
            </Form.Item>
          </Form>
        </Modal>

        {/* 导入用户模态框 */}
        <Modal
          title="批量导入用户"
          open={importModalVisible}
          onCancel={() => {
            setImportModalVisible(false);
            setImportResult(null);
          }}
          footer={[
            <Button 
              key="download" 
              icon={<DownloadOutlined />}
              onClick={handleDownloadTemplate}
            >
              下载模板
            </Button>,
            <Button 
              key="close" 
              onClick={() => {
                setImportModalVisible(false);
                setImportResult(null);
              }}
            >
              关闭
            </Button>
          ]}
          width={700}
        >
          <Typography.Paragraph>
            请上传用户数据文件，支持Excel和CSV格式。文件必须包含以下列：username、ehr_id、password、name。
            其他可选列：department、roles、team_id。
          </Typography.Paragraph>
          
          <Upload.Dragger
            name="file"
            accept=".xlsx,.xls,.csv"
            customRequest={handleImportUsers}
            showUploadList={false}
            disabled={importLoading}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持Excel和CSV格式</p>
          </Upload.Dragger>
          
          {importLoading && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Typography.Text>正在导入，请稍候...</Typography.Text>
            </div>
          )}
          
          {importResult && (
            <Card style={{ marginTop: 16 }}>
              <Typography.Title level={4}>导入结果</Typography.Title>
              <Row gutter={16}>
                <Col span={12}>
                  <Card title="成功">
                    <Typography.Text style={{ fontSize: 24, color: '#52c41a' }}>
                      {importResult.success_count}
                    </Typography.Text>
                    <Typography.Text> 个用户</Typography.Text>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="失败" bordered={false}>
                    <Typography.Text style={{ fontSize: 24, color: '#f5222d' }}>
                      {importResult.failed_count}
                    </Typography.Text>
                    <Typography.Text> 个用户</Typography.Text>
                  </Card>
                </Col>
              </Row>
              
              {importResult.failed_count > 0 && (
                <>
                  <Typography.Title level={5} style={{ marginTop: 16 }}>失败详情</Typography.Title>
                  <Table
                    dataSource={importResult.failed_users}
                    columns={[
                      { title: '行号', dataIndex: 'row', key: 'row' },
                      { title: '用户名', dataIndex: 'username', key: 'username' },
                      { title: '失败原因', dataIndex: 'reason', key: 'reason' }
                    ]}
                    size="small"
                    pagination={false}
                    rowKey={(record) => `${record.row}-${record.username}`}
                  />
                </>
              )}
            </Card>
          )}
        </Modal>
    </>
  );
};

export default UserManagement; 